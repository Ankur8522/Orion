# ORION v190 — MacBook Setup

This is the clean ORION v190 source package. It intentionally does not contain any API token, secret, or live-trading credential.

## 1. Extract
Extract this folder anywhere, for example `~/ORION`.

## 2. Verify Python
```bash
python3.13 --version
```
Python 3.13.x is recommended.

## 3. Create an isolated environment
From the ORION folder:
```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

## 4. Install ORION
```bash
python -m pip install -e .
```

## 5. Run tests
```bash
python -m pytest -q
```

## 6. Start the existing ORION runtime
Use the runtime entry point documented in `README.md` for the current release. Do not place API tokens in source files.

## 7. Kotak Neo secret
Do not paste the token into chat or commit it to Git. The production integration should retrieve it from macOS Keychain/environment secret storage. Live trading remains OFF.

## 8. Native macOS app
The native wrapper can be built with Xcode after the source/runtime is verified on this Mac. This package is source-first so Gatekeeper does not have to execute an unsigned `.command` file.
