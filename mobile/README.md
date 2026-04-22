# Snowcast Mobile

This Flutter app is the Sprint 21 mobile client scaffold.

It currently covers:
- Google sign-in
- backend token exchange
- planning search
- selected-result save to current trip
- current-trip summary and mark-checked flow

Run it with explicit runtime configuration:

```bash
flutter pub get
flutter run \
  --dart-define=API_BASE_URL=http://10.0.2.2:8000/api \
  --dart-define=GOOGLE_SERVER_CLIENT_ID=your-google-server-client-id
```

Notes:
- Android emulators should use `10.0.2.2` for a backend running on the host machine.
- iOS simulators can usually use `http://127.0.0.1:8000/api`.
- Native Google sign-in platform configuration is still required on Android/iOS before the sign-in flow will work.
