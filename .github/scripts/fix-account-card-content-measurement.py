from pathlib import Path

path = Path("src/App.tsx")
text = path.read_text(encoding="utf-8")

old = '''    const intrinsicWidth = (element: HTMLElement): number => {
      const style = window.getComputedStyle(element);
      return Math.ceil(
        Math.max(element.scrollWidth, element.getBoundingClientRect().width)
          + numericStyle(style.marginLeft)
          + numericStyle(style.marginRight),
      );
    };
'''
new = '''    const measurementCanvas = document.createElement("canvas");
    const measurementContext = measurementCanvas.getContext("2d");
    const intrinsicWidth = (element: HTMLElement): number => {
      const style = window.getComputedStyle(element);
      let contentWidth = Math.max(element.scrollWidth, element.getBoundingClientRect().width);
      if (measurementContext && element.matches("h2, .account-card-name-input")) {
        const text = element instanceof HTMLInputElement ? element.value : element.textContent ?? "";
        measurementContext.font = style.font || `${style.fontWeight} ${style.fontSize} ${style.fontFamily}`;
        const letterSpacing = numericStyle(style.letterSpacing);
        contentWidth = measurementContext.measureText(text).width
          + Math.max(0, text.length - 1) * letterSpacing
          + numericStyle(style.paddingLeft)
          + numericStyle(style.paddingRight)
          + numericStyle(style.borderLeftWidth)
          + numericStyle(style.borderRightWidth);
      }
      return Math.ceil(contentWidth + numericStyle(style.marginLeft) + numericStyle(style.marginRight));
    };
    const textIsCrowded = (element: HTMLElement): boolean => {
      if (element.scrollWidth > element.clientWidth + 1) return true;
      const lineHeight = numericStyle(window.getComputedStyle(element).lineHeight);
      return lineHeight > 0 && element.scrollHeight > lineHeight * 1.6;
    };
'''
if text.count(old) != 1:
    raise RuntimeError(f"Expected one intrinsicWidth block, found {text.count(old)}")
text = text.replace(old, new, 1)

old_crowding = '''              return Array.from(metric.querySelectorAll<HTMLElement>(".metric-heading, .metric-full-value, .metric-reset"))
                .some((element) => element.scrollWidth > element.clientWidth + 1);'''
new_crowding = '''              return Array.from(metric.querySelectorAll<HTMLElement>(".metric-heading, .metric-full-value, .metric-reset"))
                .some(textIsCrowded);'''
if text.count(old_crowding) != 1:
    raise RuntimeError(f"Expected one metric crowding block, found {text.count(old_crowding)}")
text = text.replace(old_crowding, new_crowding, 1)

path.write_text(text, encoding="utf-8")
print("Corrected account-card intrinsic content measurement")
