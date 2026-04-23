# Snowcast Mobile

This Flutter app is the thin authenticated mobile companion client.

Current scope:
- Google sign-in
- backend token exchange
- planning search
- selected-result save to current trip
- current-trip summary and mark-checked flow

Platform scope:
- iOS
- Android

Other Flutter-generated targets were intentionally removed because:
- the public demo surface is the React web app
- desktop Flutter targets are not part of the near-term product plan
- the mobile app is being kept focused on companion use cases

Run it with explicit runtime configuration:

```bash
flutter pub get
flutter run \
  --dart-define=API_BASE_URL=http://10.0.2.2:8010/api \
  --dart-define=GOOGLE_SERVER_CLIENT_ID=your-google-server-client-id
```

Notes:
- Android emulators should use `http://10.0.2.2:8010/api` for a backend running on the host machine.
- iOS simulators can usually use `http://127.0.0.1:8010/api`.
- Native Google sign-in platform configuration is still required on Android/iOS before the sign-in flow will work.
- The backend `GOOGLE_OAUTH_CLIENT_IDS` env var should allow every client audience used by the app, such as the web/server client and the iOS client.
