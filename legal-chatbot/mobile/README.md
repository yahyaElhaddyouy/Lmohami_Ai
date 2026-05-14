# Lmo7ami AI Mobile

Flutter mobile app for a Moroccan Labor Law AI chatbot.

## API configuration

Edit the backend URL in:

```text
lib/config/api_config.dart
```

Defaults:

- Android emulator: `http://10.0.2.2:8000`
- Local desktop/iOS simulator: `http://127.0.0.1:8000`
- Real phone on same Wi-Fi: change `realPhoneBaseUrl` to your computer IP.

## Run

Start the backend first:

```powershell
cd ../backend
uvicorn main:app --reload
```

Then run the Flutter app:

```powershell
flutter pub get
flutter run
```
