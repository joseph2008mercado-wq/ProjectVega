# Vega icon

`vega.svg` is the editable source: three abstract champagne slashes across six
strings on a smoked-plum glass tile. No star or text. Artwork is original to
Project Vega and uses the repository license.

`vega.ico` contains real PNG-backed icon entries at 16, 24, 32, 48, 64, 128,
and 256 pixels (supported by Vista and later). Regenerate with:

```powershell
.\.venv\Scripts\python.exe .\scripts\generate-icon.py
```

The Windows build also runs this step. The executable, Qt windows, and
shortcuts all use this same icon.
