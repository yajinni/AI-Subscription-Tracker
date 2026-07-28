// Grok billing integration is adapted from the MIT-licensed CodexBar Grok provider:
// https://github.com/steipete/CodexBar/tree/main/Sources/CodexBarCore/Providers/Grok
// The implementation reads credentials created by xAI's official `grok login`, tries
// the official Grok Build ACP billing method, and falls back to Grok's own billing
// gRPC-web surface. It never estimates messages or tokens.

use super::{ProviderError, ProviderUsage};
use crate::{
    model::{Account, GrokSecret, UsageWindow},
    state::AppState,
};
use chrono::{DateTime, TimeZone, Utc};
use reqwest::{header, StatusCode};
use serde_json::{json, Value};
use std::{
    env, fs,
    path::{Path, PathBuf},
    process::Stdio,
    time::Duration,
};
use tokio::{
    io::{AsyncBufReadExt, AsyncWriteExt, BufReader, Lines},
    process::{ChildStdout, Command},
};

const OIDC_SCOPE_PREFIX: &str = "https://auth.x.ai::";
const LEGACY_SCOPE: &str = "https://accounts.x.ai/sign-in";
const WEB_BILLING_ENDPOINT: &str =
    "https://grok.com/grok_api_v2.GrokBuildBilling/GetGrokCreditsConfig";
const INITIALIZE_TIMEOUT: Duration = Duration::from_secs(8);
const BILLING_TIMEOUT: Duration = Duration::from_secs(12);

#[derive(Clone, Debug)]
pub(crate) struct GrokCredentials {
    pub access_token: String,
    pub email: Option<String>,
    pub user_id: Option<String>,
    pub team_id: Option<String>,
    pub principal_type: Option<String>,
    pub auth_mode: Option<String>,
    pub expires_at: Option<DateTime<Utc>>,
}

impl GrokCredentials {
    pub(crate) fn is_expired(&self) -> bool {
        self.expires_at
            .is_some_and(|expires_at| expires_at <= Utc::now())
    }

    pub(crate) fn account_id(&self) -> Option<String> {
        self.user_id.clone().or_else(|| self.team_id.clone())
    }

    pub(crate) fn plan(&self) -> String {
        if self
            .principal_type
            .as_deref()
            .is_some_and(|value| value.eq_ignore_ascii_case("team"))
        {
            "Grok Team".into()
        } else if self
            .auth_mode
            .as_deref()
            .is_some_and(|value| value.eq_ignore_ascii_case("oidc"))
        {
            "SuperGrok".into()
        } else {
            "Grok".into()
        }
    }
}

#[derive(Clone, Debug)]
struct BillingSnapshot {
    used_percent: f64,
    resets_at: Option<DateTime<Utc>>,
    period_start: Option<DateTime<Utc>>,
    source: &'static str,
}

#[derive(Debug)]
enum GrokFetchError {
    Auth(String),
    Unavailable(String),
}

impl GrokFetchError {
    fn message(&self) -> &str {
        match self {
            Self::Auth(message) | Self::Unavailable(message) => message,
        }
    }
}

pub async fn refresh(
    app: &AppState,
    account: &Account,
    secret: &GrokSecret,
) -> Result<ProviderUsage, ProviderError> {
    let auth_file = if secret.auth_file.trim().is_empty() {
        default_auth_file()
    } else {
        PathBuf::from(secret.auth_file.trim())
    };
    let credentials = load_credentials(&auth_file).map_err(|_| ProviderError::Auth)?;
    if credentials.is_expired() {
        return Err(ProviderError::Auth);
    }

    let cli_result = fetch_cli_billing().await;
    let snapshot = match cli_result {
        Ok(snapshot) => snapshot,
        Err(cli_error) => match fetch_web_billing(app, &credentials).await {
            Ok(snapshot) => snapshot,
            Err(GrokFetchError::Auth(_)) => return Err(ProviderError::Auth),
            Err(web_error) => {
                return Err(ProviderError::Transient(format!(
                    "Grok did not expose billing usage through the CLI or web billing surface. CLI: {} Web: {}",
                    cli_error.message(),
                    web_error.message()
                )))
            }
        },
    };

    let used = snapshot.used_percent.clamp(0.0, 100.0);
    let (id, label, window_seconds) = classify_period(
        snapshot.period_start,
        snapshot.resets_at,
        snapshot.source == "grok_web_billing",
    );
    let window = UsageWindow {
        id: id.into(),
        label: label.into(),
        used_percent: Some(used),
        remaining_percent: Some((100.0 - used).max(0.0)),
        resets_at: snapshot.resets_at.map(|value| value.to_rfc3339()),
        window_seconds,
    };

    Ok(ProviderUsage {
        plan: Some(credentials.plan()),
        email: credentials.email.clone().or_else(|| account.email.clone()),
        provider_account_id: credentials
            .account_id()
            .or_else(|| account.provider_account_id.clone()),
        windows: vec![window],
        credits_usd: None,
        unlimited_credits: false,
        source: snapshot.source.into(),
    })
}

pub(crate) fn default_auth_file() -> PathBuf {
    grok_home().join("auth.json")
}

fn grok_home() -> PathBuf {
    if let Some(path) = env::var_os("GROK_HOME").filter(|value| !value.is_empty()) {
        return PathBuf::from(path);
    }
    env::var_os("HOME")
        .or_else(|| env::var_os("USERPROFILE"))
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from("."))
        .join(".grok")
}

pub(crate) fn find_grok_binary() -> Option<PathBuf> {
    if let Some(path) = env::var_os("GROK_BINARY").map(PathBuf::from) {
        if path.is_file() {
            return Some(path);
        }
    }

    let names: &[&str] = if cfg!(windows) {
        &["grok.exe", "grok"]
    } else {
        &["grok"]
    };
    if let Some(paths) = env::var_os("PATH") {
        for directory in env::split_paths(&paths) {
            for name in names {
                let candidate = directory.join(name);
                if candidate.is_file() {
                    return Some(candidate);
                }
            }
        }
    }

    let home = env::var_os("HOME")
        .or_else(|| env::var_os("USERPROFILE"))
        .map(PathBuf::from);
    if let Some(home) = home {
        for relative in [".local/bin/grok", ".local/bin/grok.exe"] {
            let candidate = home.join(relative);
            if candidate.is_file() {
                return Some(candidate);
            }
        }
    }

    if cfg!(target_os = "macos") {
        for candidate in ["/opt/homebrew/bin/grok", "/usr/local/bin/grok"] {
            let candidate = PathBuf::from(candidate);
            if candidate.is_file() {
                return Some(candidate);
            }
        }
    }
    None
}

pub(crate) fn load_credentials(path: &Path) -> Result<GrokCredentials, String> {
    let payload = fs::read_to_string(path)
        .map_err(|error| format!("Unable to read {}: {error}", path.display()))?;
    parse_credentials(&payload)
}

fn parse_credentials(payload: &str) -> Result<GrokCredentials, String> {
    let root: Value = serde_json::from_str(payload)
        .map_err(|error| format!("Invalid Grok auth.json: {error}"))?;
    let root = root
        .as_object()
        .ok_or_else(|| "Invalid Grok auth.json root.".to_string())?;

    let mut oidc = None;
    let mut legacy = None;
    for (scope, value) in root {
        let Some(entry) = value.as_object() else {
            continue;
        };
        let Some(token) = entry.get("key").and_then(Value::as_str) else {
            continue;
        };
        if token.trim().is_empty() {
            continue;
        }
        if scope.starts_with(OIDC_SCOPE_PREFIX) {
            oidc = Some(entry);
        } else if scope == LEGACY_SCOPE || scope.contains("/sign-in") {
            legacy = Some(entry);
        }
    }
    let entry = oidc
        .or(legacy)
        .ok_or_else(|| "Grok auth.json contains no usable access token.".to_string())?;

    Ok(GrokCredentials {
        access_token: string_field(entry, "key")
            .ok_or_else(|| "Grok auth.json is missing its access token.".to_string())?,
        email: string_field(entry, "email"),
        user_id: string_field(entry, "user_id"),
        team_id: string_field(entry, "team_id"),
        principal_type: string_field(entry, "principal_type"),
        auth_mode: string_field(entry, "auth_mode"),
        expires_at: entry.get("expires_at").and_then(parse_date_value),
    })
}

fn string_field(entry: &serde_json::Map<String, Value>, key: &str) -> Option<String> {
    entry
        .get(key)
        .and_then(Value::as_str)
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .map(str::to_string)
}

fn parse_date_value(value: &Value) -> Option<DateTime<Utc>> {
    if let Some(raw) = value.as_str() {
        if let Ok(parsed) = DateTime::parse_from_rfc3339(raw) {
            return Some(parsed.with_timezone(&Utc));
        }
        if let Ok(timestamp) = raw.parse::<i64>() {
            return timestamp_to_datetime(timestamp);
        }
    }
    value.as_i64().and_then(timestamp_to_datetime)
}

fn timestamp_to_datetime(timestamp: i64) -> Option<DateTime<Utc>> {
    let seconds = if timestamp > 10_000_000_000 {
        timestamp / 1000
    } else {
        timestamp
    };
    Utc.timestamp_opt(seconds, 0).single()
}

async fn fetch_cli_billing() -> Result<BillingSnapshot, GrokFetchError> {
    let binary = find_grok_binary().ok_or_else(|| {
        GrokFetchError::Unavailable("The official Grok Build CLI is not installed.".into())
    })?;
    let mut child = Command::new(binary)
        .args(["agent", "stdio"])
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .kill_on_drop(true)
        .spawn()
        .map_err(|error| GrokFetchError::Unavailable(format!("Unable to start Grok CLI: {error}")))?;
    let mut stdin = child
        .stdin
        .take()
        .ok_or_else(|| GrokFetchError::Unavailable("Grok CLI stdin is unavailable.".into()))?;
    let stdout = child
        .stdout
        .take()
        .ok_or_else(|| GrokFetchError::Unavailable("Grok CLI stdout is unavailable.".into()))?;
    let mut lines = BufReader::new(stdout).lines();

    send_rpc(
        &mut stdin,
        1,
        "initialize",
        json!({
            "protocolVersion": "1",
            "clientCapabilities": {
                "fs": { "readTextFile": false, "writeTextFile": false },
                "terminal": false
            }
        }),
    )
    .await?;
    let _ = read_rpc_response(&mut lines, 1, INITIALIZE_TIMEOUT).await?;

    send_rpc(&mut stdin, 2, "x.ai/billing", json!({})).await?;
    let response = read_rpc_response(&mut lines, 2, BILLING_TIMEOUT).await;
    let _ = child.kill().await;
    let _ = child.wait().await;
    parse_rpc_billing(response?)
}

async fn send_rpc(
    stdin: &mut tokio::process::ChildStdin,
    id: i64,
    method: &str,
    params: Value,
) -> Result<(), GrokFetchError> {
    let mut payload = serde_json::to_vec(&json!({
        "jsonrpc": "2.0",
        "id": id,
        "method": method,
        "params": params,
    }))
    .map_err(|error| GrokFetchError::Unavailable(format!("Unable to encode Grok RPC request: {error}")))?;
    payload.push(b'\n');
    stdin
        .write_all(&payload)
        .await
        .map_err(|error| GrokFetchError::Unavailable(format!("Unable to write to Grok CLI: {error}")))?;
    stdin
        .flush()
        .await
        .map_err(|error| GrokFetchError::Unavailable(format!("Unable to flush Grok CLI request: {error}")))
}

async fn read_rpc_response(
    lines: &mut Lines<BufReader<ChildStdout>>,
    expected_id: i64,
    timeout: Duration,
) -> Result<Value, GrokFetchError> {
    tokio::time::timeout(timeout, async {
        loop {
            let line = lines
                .next_line()
                .await
                .map_err(|error| GrokFetchError::Unavailable(format!("Unable to read Grok CLI response: {error}")))?
                .ok_or_else(|| GrokFetchError::Unavailable("Grok CLI closed before returning billing data.".into()))?;
            let Ok(value) = serde_json::from_str::<Value>(&line) else {
                continue;
            };
            if value.get("id").and_then(Value::as_i64) != Some(expected_id) {
                continue;
            }
            if let Some(error) = value.get("error") {
                let message = error
                    .get("message")
                    .and_then(Value::as_str)
                    .unwrap_or("Unknown Grok RPC error")
                    .to_string();
                let lower = message.to_ascii_lowercase();
                if lower.contains("authentication required") || lower.contains("grok login") {
                    return Err(GrokFetchError::Auth(message));
                }
                return Err(GrokFetchError::Unavailable(message));
            }
            return Ok(value);
        }
    })
    .await
    .map_err(|_| GrokFetchError::Unavailable("Grok billing RPC timed out.".into()))?
}

fn parse_rpc_billing(response: Value) -> Result<BillingSnapshot, GrokFetchError> {
    let result = response
        .get("result")
        .ok_or_else(|| GrokFetchError::Unavailable("Grok billing RPC omitted its result.".into()))?;
    let limit = nested_number(result, &["monthlyLimit", "val"])
        .ok_or_else(|| GrokFetchError::Unavailable("Grok billing RPC omitted the included limit.".into()))?;
    let used = nested_number(result, &["usage", "totalUsed", "val"])
        .or_else(|| nested_number(result, &["usage", "includedUsed", "val"]))
        .unwrap_or(0.0);
    if limit <= 0.0 {
        return Err(GrokFetchError::Unavailable(
            "Grok billing RPC returned no positive included limit.".into(),
        ));
    }
    let cycle = result.get("billingCycle");
    let period_start = cycle
        .and_then(|value| value.get("billingPeriodStart"))
        .and_then(Value::as_str)
        .and_then(parse_rfc3339);
    let resets_at = cycle
        .and_then(|value| value.get("billingPeriodEnd"))
        .and_then(Value::as_str)
        .and_then(parse_rfc3339);
    Ok(BillingSnapshot {
        used_percent: used / limit * 100.0,
        resets_at,
        period_start,
        source: "grok_build_billing_rpc",
    })
}

fn nested_number(value: &Value, path: &[&str]) -> Option<f64> {
    let mut current = value;
    for key in path {
        current = current.get(*key)?;
    }
    current
        .as_f64()
        .or_else(|| current.as_i64().map(|value| value as f64))
        .or_else(|| current.as_str()?.parse().ok())
}

fn parse_rfc3339(value: &str) -> Option<DateTime<Utc>> {
    DateTime::parse_from_rfc3339(value)
        .ok()
        .map(|value| value.with_timezone(&Utc))
}

async fn fetch_web_billing(
    app: &AppState,
    credentials: &GrokCredentials,
) -> Result<BillingSnapshot, GrokFetchError> {
    let response = app
        .client
        .post(WEB_BILLING_ENDPOINT)
        .header(header::AUTHORIZATION, format!("Bearer {}", credentials.access_token))
        .header(header::ORIGIN, "https://grok.com")
        .header(header::REFERER, "https://grok.com/?_s=usage")
        .header(header::ACCEPT, "*/*")
        .header(header::CONTENT_TYPE, "application/grpc-web+proto")
        .header("x-grpc-web", "1")
        .header("x-user-agent", "connect-es/2.1.1")
        .body(vec![0u8; 5])
        .send()
        .await
        .map_err(|error| GrokFetchError::Unavailable(format!("Grok web billing request failed: {error}")))?;
    let status = response.status();
    let headers = response.headers().clone();
    let body = response
        .bytes()
        .await
        .map_err(|error| GrokFetchError::Unavailable(format!("Unable to read Grok web billing response: {error}")))?;

    if status == StatusCode::UNAUTHORIZED || status == StatusCode::FORBIDDEN {
        return Err(GrokFetchError::Auth(
            "Grok web billing rejected the current login.".into(),
        ));
    }
    if !status.is_success() {
        return Err(GrokFetchError::Unavailable(format!(
            "Grok web billing returned HTTP {status}."
        )));
    }
    validate_grpc_status(
        headers
            .get("grpc-status")
            .and_then(|value| value.to_str().ok()),
        headers
            .get("grpc-message")
            .and_then(|value| value.to_str().ok()),
    )?;
    let trailers = grpc_trailer_fields(&body);
    validate_grpc_status(
        trailers.get("grpc-status").map(String::as_str),
        trailers.get("grpc-message").map(String::as_str),
    )?;

    let (used_percent, resets_at) = parse_web_billing_response(&body)?;
    Ok(BillingSnapshot {
        used_percent,
        resets_at,
        period_start: None,
        source: "grok_web_billing",
    })
}

fn validate_grpc_status(
    raw_status: Option<&str>,
    message: Option<&str>,
) -> Result<(), GrokFetchError> {
    let Some(status) = raw_status.and_then(|value| value.parse::<i32>().ok()) else {
        return Ok(());
    };
    if status == 0 {
        return Ok(());
    }
    let message = message.unwrap_or("Unknown Grok billing RPC error");
    let lower = message.to_ascii_lowercase();
    if status == 16
        || lower.contains("bad-credentials")
        || lower.contains("unauthenticated")
        || lower.contains("access token")
    {
        return Err(GrokFetchError::Auth(message.into()));
    }
    if status == 9 && lower.trim_end_matches('.') == "no personal team" {
        return Err(GrokFetchError::Unavailable(
            "Grok team usage is unavailable from the current billing surface.".into(),
        ));
    }
    Err(GrokFetchError::Unavailable(format!(
        "Grok web billing RPC failed with status {status}: {message}"
    )))
}

fn grpc_trailer_fields(data: &[u8]) -> std::collections::HashMap<String, String> {
    let mut fields = std::collections::HashMap::new();
    let mut index = 0usize;
    while index + 5 <= data.len() {
        let flags = data[index];
        let length = u32::from_be_bytes([
            data[index + 1],
            data[index + 2],
            data[index + 3],
            data[index + 4],
        ]) as usize;
        let start = index + 5;
        let Some(end) = start.checked_add(length) else {
            break;
        };
        if end > data.len() {
            break;
        }
        if flags & 0x80 != 0 {
            if let Ok(text) = std::str::from_utf8(&data[start..end]) {
                for line in text.lines() {
                    if let Some((key, value)) = line.split_once(':') {
                        fields.insert(
                            key.trim().to_ascii_lowercase(),
                            value.trim().to_string(),
                        );
                    }
                }
            }
        }
        index = end;
    }
    fields
}

#[derive(Default)]
struct ProtobufScan {
    fixed32: Vec<Fixed32Field>,
    varints: Vec<VarintField>,
}

struct Fixed32Field {
    path: Vec<u64>,
    value: f32,
    order: usize,
}

struct VarintField {
    path: Vec<u64>,
    value: u64,
}

impl ProtobufScan {
    fn merge(&mut self, mut other: Self) {
        self.fixed32.append(&mut other.fixed32);
        self.varints.append(&mut other.varints);
    }
}

fn parse_web_billing_response(
    data: &[u8],
) -> Result<(f64, Option<DateTime<Utc>>), GrokFetchError> {
    let mut payloads = grpc_data_frames(data);
    if payloads.is_empty() && looks_like_protobuf(data) {
        payloads.push(data.to_vec());
    }
    if payloads.is_empty() {
        return Err(GrokFetchError::Unavailable(
            "Grok web billing returned no protobuf payload.".into(),
        ));
    }

    let mut scan = ProtobufScan::default();
    for payload in payloads {
        let (nested, _) = scan_protobuf(&payload, 0, Vec::new(), 0);
        scan.merge(nested);
    }
    let percent = scan
        .fixed32
        .iter()
        .filter(|field| {
            field.path.last() == Some(&1)
                && field.value.is_finite()
                && (0.0..=100.0).contains(&field.value)
        })
        .min_by_key(|field| (field.path.len(), field.order))
        .map(|field| field.value as f64);

    let now = Utc::now();
    let future_resets = scan
        .varints
        .iter()
        .filter_map(|field| {
            if !(1_700_000_000..=2_100_000_000).contains(&field.value) {
                return None;
            }
            let date = Utc.timestamp_opt(field.value as i64, 0).single()?;
            (date > now).then_some((field.path.as_slice(), date))
        })
        .collect::<Vec<_>>();
    let resets_at = future_resets
        .iter()
        .filter(|(path, _)| *path == [1, 5, 1])
        .map(|(_, date)| *date)
        .min()
        .or_else(|| future_resets.iter().map(|(_, date)| *date).min());
    let has_usage_period = scan.varints.iter().any(|field| {
        field.path.starts_with(&[1, 6])
            || (field.path == [1, 8, 1] && (field.value == 1 || field.value == 2))
    });
    let used_percent = percent
        .or_else(|| {
            (scan.fixed32.is_empty() && resets_at.is_some() && has_usage_period).then_some(0.0)
        })
        .ok_or_else(|| {
            GrokFetchError::Unavailable("Could not parse Grok web billing usage.".into())
        })?;
    Ok((used_percent, resets_at))
}

fn grpc_data_frames(data: &[u8]) -> Vec<Vec<u8>> {
    let mut frames = Vec::new();
    let mut index = 0usize;
    while index < data.len() {
        if index + 5 > data.len() {
            return Vec::new();
        }
        let flags = data[index];
        let length = u32::from_be_bytes([
            data[index + 1],
            data[index + 2],
            data[index + 3],
            data[index + 4],
        ]) as usize;
        let start = index + 5;
        let Some(end) = start.checked_add(length) else {
            return Vec::new();
        };
        if end > data.len() {
            return Vec::new();
        }
        if flags & 0x80 == 0 {
            frames.push(data[start..end].to_vec());
        }
        index = end;
    }
    frames
}

fn looks_like_protobuf(data: &[u8]) -> bool {
    data.first().is_some_and(|first| {
        let field = first >> 3;
        let wire = first & 0x07;
        field > 0 && matches!(wire, 0 | 1 | 2 | 5)
    })
}

fn scan_protobuf(
    data: &[u8],
    depth: usize,
    path: Vec<u64>,
    order: usize,
) -> (ProtobufScan, usize) {
    let mut scan = ProtobufScan::default();
    let mut index = 0usize;
    let mut next_order = order;
    while index < data.len() {
        let field_start = index;
        let Some(key) = read_varint(data, &mut index).filter(|key| *key != 0) else {
            index = field_start + 1;
            continue;
        };
        let field_number = key >> 3;
        let wire_type = key & 0x07;
        let mut field_path = path.clone();
        field_path.push(field_number);
        match wire_type {
            0 => {
                if let Some(value) = read_varint(data, &mut index) {
                    scan.varints.push(VarintField {
                        path: field_path,
                        value,
                    });
                } else {
                    index = field_start + 1;
                }
            }
            1 => {
                if index + 8 > data.len() {
                    break;
                }
                index += 8;
            }
            2 => {
                let Some(length) = read_varint(data, &mut index) else {
                    index = field_start + 1;
                    continue;
                };
                let Ok(length) = usize::try_from(length) else {
                    index = field_start + 1;
                    continue;
                };
                let Some(end) = index.checked_add(length) else {
                    index = field_start + 1;
                    continue;
                };
                if end > data.len() {
                    index = field_start + 1;
                    continue;
                }
                if depth < 4 {
                    let (nested, nested_order) = scan_protobuf(
                        &data[index..end],
                        depth + 1,
                        field_path,
                        next_order,
                    );
                    scan.merge(nested);
                    next_order = nested_order;
                }
                index = end;
            }
            5 => {
                if index + 4 > data.len() {
                    break;
                }
                let bits = u32::from_le_bytes([
                    data[index],
                    data[index + 1],
                    data[index + 2],
                    data[index + 3],
                ]);
                scan.fixed32.push(Fixed32Field {
                    path: field_path,
                    value: f32::from_bits(bits),
                    order: next_order,
                });
                next_order += 1;
                index += 4;
            }
            _ => index = field_start + 1,
        }
    }
    (scan, next_order)
}

fn read_varint(data: &[u8], index: &mut usize) -> Option<u64> {
    let mut value = 0u64;
    let mut shift = 0u32;
    while *index < data.len() && shift < 64 {
        let byte = data[*index];
        *index += 1;
        value |= u64::from(byte & 0x7f) << shift;
        if byte & 0x80 == 0 {
            return Some(value);
        }
        shift += 7;
    }
    None
}

fn classify_period(
    start: Option<DateTime<Utc>>,
    end: Option<DateTime<Utc>>,
    web_weekly: bool,
) -> (&'static str, &'static str, Option<u64>) {
    if let (Some(start), Some(end)) = (start, end) {
        let seconds = (end - start).num_seconds();
        if (5 * 86_400..=9 * 86_400).contains(&seconds) {
            return ("weekly", "Weekly", Some(seconds as u64));
        }
        if (25 * 86_400..=35 * 86_400).contains(&seconds) {
            return ("monthly", "Monthly", Some(seconds as u64));
        }
        if seconds > 0 {
            return ("credits", "Credits", Some(seconds as u64));
        }
    }
    if web_weekly {
        ("weekly", "Weekly", Some(604_800))
    } else {
        ("credits", "Credits", None)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn encode_varint(mut value: u64, output: &mut Vec<u8>) {
        loop {
            let mut byte = (value & 0x7f) as u8;
            value >>= 7;
            if value != 0 {
                byte |= 0x80;
            }
            output.push(byte);
            if value == 0 {
                break;
            }
        }
    }

    fn length_field(field: u64, payload: &[u8], output: &mut Vec<u8>) {
        encode_varint((field << 3) | 2, output);
        encode_varint(payload.len() as u64, output);
        output.extend_from_slice(payload);
    }

    fn varint_field(field: u64, value: u64, output: &mut Vec<u8>) {
        encode_varint(field << 3, output);
        encode_varint(value, output);
    }

    fn fixture(percent: Option<f32>, reset: u64) -> Vec<u8> {
        let mut period = Vec::new();
        if let Some(percent) = percent {
            encode_varint((1 << 3) | 5, &mut period);
            period.extend_from_slice(&percent.to_bits().to_le_bytes());
        }
        let mut reset_message = Vec::new();
        varint_field(1, reset, &mut reset_message);
        length_field(5, &reset_message, &mut period);
        varint_field(6, 1, &mut period);
        let mut root = Vec::new();
        length_field(1, &period, &mut root);
        let mut framed = vec![0, 0, 0, 0, 0];
        let length = (root.len() as u32).to_be_bytes();
        framed[1..5].copy_from_slice(&length);
        framed.extend_from_slice(&root);
        framed
    }

    #[test]
    fn prefers_supergrok_oidc_credentials() {
        let parsed = parse_credentials(
            r#"{
              "https://accounts.x.ai/sign-in":{"key":"legacy","email":"old@example.com"},
              "https://auth.x.ai::client":{"key":"oidc","auth_mode":"oidc","email":"new@example.com","user_id":"u1","expires_at":"2099-01-01T00:00:00Z"}
            }"#,
        )
        .unwrap();
        assert_eq!(parsed.access_token, "oidc");
        assert_eq!(parsed.email.as_deref(), Some("new@example.com"));
        assert_eq!(parsed.plan(), "SuperGrok");
    }

    #[test]
    fn parses_provider_reported_percent_and_reset() {
        let reset = (Utc::now().timestamp() + 86_400) as u64;
        let (percent, parsed_reset) = parse_web_billing_response(&fixture(Some(42.5), reset)).unwrap();
        assert!((percent - 42.5).abs() < 0.01);
        assert_eq!(parsed_reset.unwrap().timestamp(), reset as i64);
    }

    #[test]
    fn treats_omitted_proto3_percent_as_zero_for_active_period() {
        let reset = (Utc::now().timestamp() + 86_400) as u64;
        let (percent, _) = parse_web_billing_response(&fixture(None, reset)).unwrap();
        assert_eq!(percent, 0.0);
    }

    #[test]
    fn classifies_common_billing_cycles() {
        let start = Utc::now();
        assert_eq!(
            classify_period(Some(start), Some(start + chrono::Duration::days(7)), false).0,
            "weekly"
        );
        assert_eq!(
            classify_period(Some(start), Some(start + chrono::Duration::days(30)), false).0,
            "monthly"
        );
    }
}
