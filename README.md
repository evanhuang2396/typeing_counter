# DevTypingTracker

隱私友善的 Windows 背景打字量追蹤工具（僅記錄按鍵次數，不記錄按鍵內容）。

## 安裝

```bash
pip install -r requirements.txt
```

## 執行

Windows 背景執行（無 CMD 視窗）：

```bat
start_tracker.bat
```

或直接執行：

```bash
python tracker.py
```

## 輸出

程式每 60 秒輸出一次資料到 `daily_typing.csv`，格式如下：

```csv
timestamp,keystroke_count
2026-04-19 10:00,152
```

## 測試

```bash
python test_logic.py
```
