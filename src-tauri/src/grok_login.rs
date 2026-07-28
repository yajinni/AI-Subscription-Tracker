use crate::{
    model::{now_rfc3339, Account, GrokSecret, LoginStart, LoginStatus, Provider, ProviderSecret},
    providers::grok::{default_auth_file, find_grok_binary, load_credentials},
    state::AppState,
    store::save_provider_secret,
    usage,
};
use chrono::{Duration as ChronoDuration, Utc};
use std::{process::Stdio, sync::Arc, time::Duration};
use tokio::process::Command;
use uuid::Uuid;

const LOGIN_TIMEOUT: Duration = Duration::from_secs(10 * 60);

pub async fn start_login(app: Arc<AppState>, label: String) -> Result<LoginStart, String> {
    if app
        .pending_login
        .read()
        .as_ref()
        .is_some_and(|login| login.status == "waiting")
    {
        return Err("Another provider login is already in progress.".into());
    }

    let binary = find_grok_binary().ok_or_else(install_message)?;
    let attempt_id = Uuid::new_v4().to_string();
    let expires_at = (Utc::now() + ChronoDuration::minutes(10)).to_rfc3339();
    *app.pending_login.write() = Some(LoginStatus {
        attempt_id: attempt_id.clone(),
        status: "waiting".into(),
        message: Some(
            "The official Grok Build login is opening. Finish signing in through xAI in your browser."
                .into(),
        ),
        account: None,
    });

    let task_app = app.clone();
    let task_attempt = attempt_id.clone();
    tokio::spawn(async move {
        let result = complete_login(task_app.clone(), label, binary).await;
        match result {
            Ok(account) => {
                *task_app.pending_login.write() = Some(LoginStatus {
                    attempt_id: task_attempt,
                    status: "complete".into(),
                    message: None,
                    account: Some(account),
                });
            }
            Err(error) => {
                *task_app.pending_login.write() = Some(LoginStatus {
                    attempt_id: task_attempt,
                    status: "failed".into(),
                    message: Some(error),
                    account: None,
                });
            }
        }
    });

    Ok(LoginStart {
        attempt_id,
        authorization_url: String::new(),
        expires_at,
    })
}

async fn complete_login(
    app: Arc<AppState>,
    label: String,
    binary: std::path::PathBuf,
) -> Result<Account, String> {
    let mut command = Command::new(binary);
    command
        .arg("login")
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .kill_on_drop(true);
    let output = tokio::time::timeout(LOGIN_TIMEOUT, command.output())
        .await
        .map_err(|_| "Grok login timed out. Start it again and finish the browser sign-in within ten minutes.".to_string())?
        .map_err(|error| format!("Unable to start the official Grok Build login: {error}"))?;
    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        let message = stderr
            .lines()
            .map(str::trim)
            .filter(|line| !line.is_empty())
            .take(4)
            .collect::<Vec<_>>()
            .join(" ");
        return Err(if message.is_empty() {
            format!("Grok login exited with {}.", output.status)
        } else {
            format!("Grok login failed: {message}")
        });
    }

    let auth_file = default_auth_file();
    let mut credentials = None;
    let mut last_error = None;
    // The CLI normally writes auth.json before it exits, but antivirus or file
    // synchronization can delay visibility briefly after browser completion.
    for attempt in 0..=20 {
        match load_credentials(&auth_file) {
            Ok(candidate) if !candidate.is_expired() => {
                credentials = Some(candidate);
                break;
            }
            Ok(_) => last_error = Some("The Grok login produced an expired credential.".into()),
            Err(error) => last_error = Some(error),
        }
        if attempt < 20 {
            tokio::time::sleep(Duration::from_millis(250)).await;
        }
    }
    let credentials = credentials.ok_or_else(|| {
        format!(
            "Grok login finished, but the tracker could not load {}. {}",
            auth_file.display(),
            last_error.unwrap_or_else(|| "Run `grok login` again.".into())
        )
    })?;

    let provider_account_id = credentials.account_id();
    let duplicate = app.store.find_duplicate(
        &Provider::Grok,
        provider_account_id.as_deref(),
        credentials.email.as_deref(),
    );
    let now = now_rfc3339();
    let account_id = duplicate
        .as_ref()
        .map(|account| account.id.clone())
        .unwrap_or_else(|| Uuid::new_v4().to_string());
    let account = Account {
        id: account_id.clone(),
        label: if label.trim().is_empty() {
            credentials
                .email
                .clone()
                .unwrap_or_else(|| "Grok / SuperGrok".into())
        } else {
            label.trim().to_string()
        },
        provider: Provider::Grok,
        email: credentials
            .email
            .clone()
            .or_else(|| duplicate.as_ref().and_then(|account| account.email.clone())),
        provider_account_id: provider_account_id.or_else(|| {
            duplicate
                .as_ref()
                .and_then(|account| account.provider_account_id.clone())
        }),
        chatgpt_account_id: None,
        plan: Some(credentials.plan()),
        created_at: duplicate
            .as_ref()
            .map(|account| account.created_at.clone())
            .unwrap_or_else(|| now.clone()),
        updated_at: now,
        last_usage: duplicate
            .as_ref()
            .and_then(|account| account.last_usage.clone()),
        last_error: None,
        auth_required: false,
    };
    save_provider_secret(
        &account_id,
        &ProviderSecret::Grok(GrokSecret {
            auth_file: auth_file.to_string_lossy().to_string(),
        }),
    )
    .map_err(|error| format!("Unable to save the Grok connection: {error}"))?;
    app.store
        .upsert(account)
        .map_err(|error| format!("Unable to save the Grok account: {error}"))?;

    match usage::refresh_account(app.clone(), &account_id).await {
        Ok(account) => Ok(account),
        Err(_) => app
            .store
            .get(&account_id)
            .ok_or_else(|| "The Grok account disappeared after login.".to_string()),
    }
}

fn install_message() -> String {
    if cfg!(windows) {
        "The official Grok Build CLI was not found. Install it in PowerShell with `irm https://x.ai/cli/install.ps1 | iex`, restart the tracker, and try again."
            .into()
    } else {
        "The official Grok Build CLI was not found. Install it with `curl -fsSL https://x.ai/cli/install.sh | bash`, restart the tracker, and try again."
            .into()
    }
}
