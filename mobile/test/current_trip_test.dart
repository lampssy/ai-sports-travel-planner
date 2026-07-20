import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:snowcast_mobile/main.dart';

Map<String, dynamic> _summaryJson({
  String freshnessStatus = 'fresh',
  String basisSummary = 'Weather evidence for the saved trip window.',
  String sourceType = 'forecast',
}) => {
  'trip': {
    'ski_region_name': 'Chamonix Valley',
    'focus_ski_area_name': 'Grands Montets',
    'stay_base_name': 'Argentiere',
    'trip_start_date': '2026-04-09',
    'trip_end_date': '2026-04-16',
  },
  'current_conditions': {'weather_summary': 'Fresh snow is likely this week.'},
  'current_conditions_provenance': {
    'freshness_status': freshnessStatus,
    'basis_summary': basisSummary,
    'source_type': sourceType,
  },
  'comparison_basis': {'label': 'internal baseline'},
  'companion_status': {
    'trip_window_label': 'internal trip window',
    'eligibility_reason': 'The trip is close enough for useful updates.',
  },
  'delta': {
    'summary': 'Conditions are similar to the last check.',
    'changes': ['Snow depth increased.'],
  },
};

Map<String, dynamic> _eventsJson() => {
  'events': [
    {
      'summary': 'Snow depth increased after fresh snowfall.',
      'recorded_at': '2026-04-08T10:15:00Z',
      'actionable': true,
    },
  ],
};

AppSession _session() => AppSession(
  accessToken: 'token',
  expiresAt: '2026-07-03T00:00:00Z',
  user: AppUser(userId: 'user-1', email: 'user@example.com'),
);

Future<AuthController> _authController(
  MobileApiClient api, {
  SessionStore? store,
}) async {
  final sessionStore = store ?? InMemorySessionStore();
  await sessionStore.write(_session());
  final controller = AuthController(api: api, sessionStore: sessionStore);
  await controller.restoreSession();
  return controller;
}

void main() {
  testWidgets(
    'session expiry clears persisted auth and returns to reachable sign-in',
    (tester) async {
      final store = InMemorySessionStore();
      final api = MobileApiClient(
        baseUrl: 'http://localhost/api',
        client: MockClient((request) async {
          if (request.url.path == '/api/current-trip/summary') {
            return http.Response('{"error":{"code":"session_expired"}}', 401);
          }
          return http.Response(jsonEncode(_eventsJson()), 200);
        }),
      );
      final auth = await _authController(api, store: store);

      await tester.pumpWidget(SnowcastApp(api: api, authController: auth));
      await tester.tap(find.text('Current trip').last);
      await tester.pumpAndSettle();

      expect(await store.read(), isNull);
      expect(find.text('Sign in to Snowcast'), findsOneWidget);
      expect(find.text('Sign in with Google'), findsOneWidget);
      expect(find.text('Your session ended. Sign in again.'), findsOneWidget);
      expect(
        tester.getSemantics(find.text('Sign in to Snowcast')),
        matchesSemantics(
          label: 'Sign in to Snowcast',
          isHeader: true,
          isFocused: true,
          isFocusable: true,
          hasFocusAction: true,
        ),
      );
      expect(
        tester.getSemantics(find.text('Your session ended. Sign in again.')),
        matchesSemantics(
          label: 'Your session ended. Sign in again.',
          isLiveRegion: true,
        ),
      );
    },
  );

  testWidgets(
    'authentication required clears persisted auth and returns to sign-in',
    (tester) async {
      final store = InMemorySessionStore();
      final api = MobileApiClient(
        baseUrl: 'http://localhost/api',
        client: MockClient(
          (request) async => http.Response(
            '{"error":{"code":"authentication_required"}}',
            401,
          ),
        ),
      );
      final auth = await _authController(api, store: store);

      await tester.pumpWidget(SnowcastApp(api: api, authController: auth));
      await tester.tap(find.text('Current trip').last);
      await tester.pumpAndSettle();

      expect(await store.read(), isNull);
      expect(find.text('Sign in to Snowcast'), findsOneWidget);
      expect(find.text('Sign in to continue.'), findsOneWidget);
    },
  );

  testWidgets('loads summary and trip updates independently', (tester) async {
    final api = MobileApiClient(
      baseUrl: 'http://localhost/api',
      client: MockClient((request) async {
        if (request.url.path == '/api/current-trip/summary') {
          return http.Response('{"error":{"code":"request_failed"}}', 500);
        }
        return http.Response(jsonEncode(_eventsJson()), 200);
      }),
    );
    final auth = await _authController(api);

    await tester.pumpWidget(
      MaterialApp(
        home: CurrentTripScreen(
          api: api,
          session: _session(),
          authController: auth,
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(
      find.text('Your current trip could not be loaded. Try again.'),
      findsOneWidget,
    );
    expect(find.text('Trip updates'), findsOneWidget);
    expect(
      find.text('Snow depth increased after fresh snowfall.'),
      findsOneWidget,
    );
    expect(
      find.bySemanticsLabel('Try loading current trip again'),
      findsOneWidget,
    );
  });

  testWidgets('labels current-trip weather by freshness', (tester) async {
    for (final entry in <String, (String, String, String)>{
      'fresh': (
        'Current conditions',
        'The latest forecast was updated recently.',
        'forecast',
      ),
      'stale': (
        'Latest available conditions (out of date)',
        'The latest available forecast is out of date.',
        'forecast',
      ),
      'unknown-forecast': (
        'Latest available conditions',
        'The forecast update time is unavailable.',
        'forecast',
      ),
      'estimated': (
        'Estimated conditions',
        'No forecast is available, so these conditions are estimated.',
        'estimated',
      ),
    }.entries) {
      final freshnessStatus =
          entry.key == 'unknown-forecast' || entry.key == 'estimated'
          ? 'unknown'
          : entry.key;
      final api = MobileApiClient(
        baseUrl: 'http://localhost/api',
        client: MockClient((request) async {
          if (request.url.path == '/api/current-trip/summary') {
            return http.Response(
              jsonEncode(
                _summaryJson(
                  freshnessStatus: freshnessStatus,
                  basisSummary: entry.value.$2,
                  sourceType: entry.value.$3,
                ),
              ),
              200,
            );
          }
          return http.Response(jsonEncode(_eventsJson()), 200);
        }),
      );
      final auth = await _authController(api);

      await tester.pumpWidget(
        MaterialApp(
          home: CurrentTripScreen(
            key: ValueKey(entry.key),
            api: api,
            session: _session(),
            authController: auth,
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text(entry.value.$1), findsOneWidget);
      expect(find.text(entry.value.$2), findsOneWidget);
    }
  });

  testWidgets('current-trip not found shows the normal empty state', (
    tester,
  ) async {
    final api = MobileApiClient(
      baseUrl: 'http://localhost/api',
      client: MockClient(
        (request) async =>
            http.Response('{"error":{"code":"current_trip_not_found"}}', 404),
      ),
    );
    final auth = await _authController(api);

    await tester.pumpWidget(
      MaterialApp(
        home: CurrentTripScreen(
          api: api,
          session: _session(),
          authController: auth,
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('No current trip is saved.'), findsOneWidget);
    expect(find.textContaining('could not be loaded'), findsNothing);
    expect(find.text('Trip updates'), findsNothing);
  });

  testWidgets('keeps prior events when post-action refresh fails', (
    tester,
  ) async {
    var eventCalls = 0;
    final api = MobileApiClient(
      baseUrl: 'http://localhost/api',
      client: MockClient((request) async {
        switch (request.url.path) {
          case '/api/current-trip/summary':
            return http.Response(jsonEncode(_summaryJson()), 200);
          case '/api/current-trip/events':
            eventCalls += 1;
            return eventCalls == 1
                ? http.Response(jsonEncode(_eventsJson()), 200)
                : http.Response('{"error":{"code":"request_failed"}}', 500);
          case '/api/current-trip/mark-checked':
            return http.Response('{}', 200);
        }
        return http.Response('{}', 404);
      }),
    );
    final auth = await _authController(api);

    await tester.pumpWidget(
      MaterialApp(
        home: CurrentTripScreen(
          api: api,
          session: _session(),
          authController: auth,
        ),
      ),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.text('Mark conditions as reviewed'));
    await tester.pumpAndSettle();

    expect(
      find.text('Snow depth increased after fresh snowfall.'),
      findsOneWidget,
    );
    expect(find.text('April 9, 2026 to April 16, 2026'), findsOneWidget);
    expect(find.text('April 8, 2026'), findsOneWidget);
    expect(find.textContaining('2026-04-'), findsNothing);
    expect(find.textContaining('internal baseline'), findsNothing);
    expect(find.textContaining('internal trip window'), findsNothing);
    expect(find.textContaining('Actionable'), findsNothing);
    expect(find.textContaining('Companion history'), findsNothing);
    expect(
      find.text('Trip updates could not be loaded. Try again.'),
      findsOneWidget,
    );
    expect(
      find.bySemanticsLabel('Try loading trip updates again'),
      findsOneWidget,
    );
  });

  testWidgets('mark-checked failure preserves data and retries locally', (
    tester,
  ) async {
    var markCalls = 0;
    final api = MobileApiClient(
      baseUrl: 'http://localhost/api',
      client: MockClient((request) async {
        switch (request.url.path) {
          case '/api/current-trip/summary':
            return http.Response(jsonEncode(_summaryJson()), 200);
          case '/api/current-trip/events':
            return http.Response(jsonEncode(_eventsJson()), 200);
          case '/api/current-trip/mark-checked':
            markCalls += 1;
            return markCalls == 1
                ? http.Response('{"error":{"code":"request_failed"}}', 500)
                : http.Response('{}', 200);
        }
        return http.Response('{}', 404);
      }),
    );
    final auth = await _authController(api);

    await tester.pumpWidget(
      MaterialApp(
        home: CurrentTripScreen(
          api: api,
          session: _session(),
          authController: auth,
        ),
      ),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.text('Mark conditions as reviewed'));
    await tester.pumpAndSettle();

    expect(find.text('Chamonix Valley'), findsOneWidget);
    expect(
      find.text('Snow depth increased after fresh snowfall.'),
      findsOneWidget,
    );
    expect(
      find.text('Your current trip could not be updated. Try again.'),
      findsOneWidget,
    );
    expect(
      find.bySemanticsLabel('Try marking conditions as reviewed again'),
      findsOneWidget,
    );
    expect(
      tester.getSemantics(
        find.bySemanticsLabel('Try marking conditions as reviewed again'),
      ),
      matchesSemantics(
        label: 'Try marking conditions as reviewed again',
        isButton: true,
        hasTapAction: true,
      ),
    );
    expect(
      tester.getSemantics(
        find.text('Your current trip could not be updated. Try again.'),
      ),
      matchesSemantics(
        label: 'Your current trip could not be updated. Try again.',
        isLiveRegion: true,
      ),
    );

    await tester.tap(
      find.bySemanticsLabel('Try marking conditions as reviewed again'),
    );
    await tester.pumpAndSettle();

    expect(markCalls, 2);
    expect(
      find.text('Your current trip could not be updated. Try again.'),
      findsNothing,
    );
  });

  testWidgets('recovery controls reflow at enlarged text scale', (
    tester,
  ) async {
    final api = MobileApiClient(
      baseUrl: 'http://localhost/api',
      client: MockClient(
        (request) async =>
            http.Response('{"error":{"code":"request_failed"}}', 500),
      ),
    );
    final auth = await _authController(api);

    await tester.pumpWidget(
      MaterialApp(
        home: MediaQuery(
          data: const MediaQueryData(
            size: Size(320, 700),
            textScaler: TextScaler.linear(2),
          ),
          child: CurrentTripScreen(
            api: api,
            session: _session(),
            authController: auth,
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    final retry = find.bySemanticsLabel('Try loading current trip again');
    expect(retry, findsOneWidget);
    expect(tester.getSize(retry).height, greaterThanOrEqualTo(48));
    expect(tester.takeException(), isNull);
  });
}
