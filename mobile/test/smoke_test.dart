import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:snowcast_mobile/main.dart';

Map<String, dynamic> recommendationGroupJson() => {
  'ski_region_id': 'chamonix-valley',
  'ski_region_name': 'Chamonix Valley',
  'rank': 1,
  'fit_score': 84.0,
  'top_configuration': {
    'candidate_id': 'argentiere-grands-montets--chamonix-le-pass',
    'ski_region_id': 'chamonix-valley',
    'ski_region_name': 'Chamonix Valley',
    'stay_destination_id': 'chamonix-mont-blanc',
    'stay_destination_name': 'Chamonix-Mont-Blanc',
    'stay_base_id': 'chamonix-mont-blanc-argentiere',
    'stay_base_name': 'Argentiere',
    'ski_area_id': 'grands-montets',
    'ski_area_name': 'Grands Montets',
    'access': {
      'ski_area_access_id': 'argentiere-grands-montets',
      'access_mode': 'walk',
      'lift_distance': 'near',
      'nearest_lift_name': 'Plan Joran',
      'distance_m': 450,
      'duration_minutes': 7,
      'is_direct': true,
    },
    'selected_pass': {
      'lift_pass_product_id': 'chamonix-le-pass',
      'name': 'Chamonix Le Pass',
      'validity_scope': 'local_multi_area',
      'covered_ski_area_ids': ['grands-montets'],
      'accessible_piste_km': 115,
      'accessible_piste_km_evidence': {
        'trust_status': 'verified',
        'scope': 'pass',
        'source_entity_id': 'chamonix-le-pass',
        'field_group': 'pass_accessible_terrain',
      },
      'price': null,
    },
    'lodging_estimate': null,
    'ranking_status': 'ranked',
    'fit_score': 84.0,
    'groups': <Map<String, dynamic>>[],
    'factors': <Map<String, dynamic>>[],
    'constraint_warnings': <Map<String, dynamic>>[],
  },
  'alternative_configurations': <Map<String, dynamic>>[],
};

Map<String, dynamic> searchResponseJson({
  Map<String, dynamic> travelWindow = const {'month': 3},
}) => {
  'search_model_version': 'search-v4',
  'ranking_policy_version': 'search-v4-policy-1',
  'ranking_status': 'ranked',
  'unscored_reason': null,
  'applied_intent': {
    'constraints': {'travel_window': travelWindow},
  },
  'eligible_candidate_count': 1,
  'excluded_candidate_count': 0,
  'results': [recommendationGroupJson()],
  'refinements': [
    {
      'question_id': 'ignored-on-mobile',
      'question': 'A dynamic question',
      'reason': 'Mobile safely ignores this optional field.',
      'options': <Map<String, dynamic>>[],
    },
  ],
};

void main() {
  testWidgets('renders mobile sign-in screen', (tester) async {
    await tester.pumpWidget(
      SnowcastApp(
        api: MobileApiClient(baseUrl: 'http://localhost/api'),
        authController: AuthController(
          api: MobileApiClient(baseUrl: 'http://localhost/api'),
          sessionStore: InMemorySessionStore(),
        ),
      ),
    );

    expect(find.text('Sign in to Snowcast'), findsOneWidget);
    expect(find.text('Sign in with Google'), findsOneWidget);
    expect(find.textContaining('API base:'), findsNothing);
  });

  test('mobile search POSTs V4 intent with exact-date precedence', () async {
    late http.Request request;
    final api = MobileApiClient(
      baseUrl: 'http://localhost/api',
      client: MockClient((incoming) async {
        request = incoming;
        return http.Response(jsonEncode(searchResponseJson()), 200);
      }),
    );

    final response = await api.search(
      location: 'France',
      maxPrice: 320,
      stars: 2,
      skillLevel: 'intermediate',
      travelMonth: 3,
      tripStartDate: '2026-04-09',
      tripEndDate: '2026-04-16',
    );

    expect(request.method, 'POST');
    expect(request.url.path, '/api/search');
    final body = jsonDecode(request.body) as Map<String, dynamic>;
    final intent = body['intent'] as Map<String, dynamic>;
    final constraints = intent['constraints'] as Map<String, dynamic>;
    expect(constraints['travel_window'], {
      'start_date': '2026-04-09',
      'end_date': '2026-04-16',
    });
    expect(
      (constraints['travel_window'] as Map<String, dynamic>).containsKey(
        'month',
      ),
      isFalse,
    );
    expect(body['generate_refinements'], isFalse);
    expect(response.searchModelVersion, 'search-v4');
    expect(response.rankingPolicyVersion, 'search-v4-policy-1');
    expect(response.results.single.topConfiguration.fitScore, 84.0);
  });

  testWidgets('mobile save keeps the month used for displayed results', (
    tester,
  ) async {
    Map<String, dynamic>? savedBody;
    final api = MobileApiClient(
      baseUrl: 'http://localhost/api',
      client: MockClient((request) async {
        if (request.url.path == '/api/search') {
          return http.Response(jsonEncode(searchResponseJson()), 200);
        }
        if (request.url.path == '/api/current-trip') {
          savedBody = jsonDecode(request.body) as Map<String, dynamic>;
          return http.Response('{}', 200);
        }
        return http.Response('{}', 404);
      }),
    );
    final session = AppSession(
      accessToken: 'token',
      expiresAt: '2026-07-03T00:00:00Z',
      user: AppUser(userId: 'user-1', email: 'user@example.com'),
    );

    await tester.pumpWidget(
      MaterialApp(
        home: SearchScreen(
          api: api,
          session: session,
          authController: AuthController(
            api: api,
            sessionStore: InMemorySessionStore(),
          ),
        ),
      ),
    );
    await tester.tap(find.widgetWithText(OutlinedButton, 'Search'));
    await tester.pumpAndSettle();

    final monthField = find.byWidgetPredicate(
      (widget) =>
          widget is DropdownButtonFormField<int?> &&
          widget.decoration.labelText == 'Travel month (optional)',
    );
    await tester.ensureVisible(monthField);
    await tester.tap(monthField);
    await tester.pumpAndSettle();
    await tester.tap(find.text('April').last);
    await tester.pumpAndSettle();

    final save = find.widgetWithText(FilledButton, 'Save as current trip');
    await tester.ensureVisible(save);
    await tester.tap(save);
    await tester.pumpAndSettle();

    expect(savedBody, containsPair('travel_month', 3));
    expect(savedBody, containsPair('trip_start_date', null));
    expect(savedBody, containsPair('trip_end_date', null));
  });

  testWidgets('mobile save keeps the exact dates used for displayed results', (
    tester,
  ) async {
    Map<String, dynamic>? savedBody;
    final api = MobileApiClient(
      baseUrl: 'http://localhost/api',
      client: MockClient((request) async {
        if (request.url.path == '/api/parse-query') {
          return http.Response(
            jsonEncode({
              'filters': {
                'trip_start_date': '2026-04-09',
                'trip_end_date': '2026-04-16',
              },
            }),
            200,
          );
        }
        if (request.url.path == '/api/search') {
          return http.Response(
            jsonEncode(
              searchResponseJson(
                travelWindow: const {
                  'start_date': '2026-04-09',
                  'end_date': '2026-04-16',
                },
              ),
            ),
            200,
          );
        }
        if (request.url.path == '/api/current-trip') {
          savedBody = jsonDecode(request.body) as Map<String, dynamic>;
          return http.Response('{}', 200);
        }
        return http.Response('{}', 404);
      }),
    );
    final session = AppSession(
      accessToken: 'token',
      expiresAt: '2026-07-03T00:00:00Z',
      user: AppUser(userId: 'user-1', email: 'user@example.com'),
    );

    await tester.pumpWidget(
      MaterialApp(
        home: SearchScreen(
          api: api,
          session: session,
          authController: AuthController(
            api: api,
            sessionStore: InMemorySessionStore(),
          ),
        ),
      ),
    );
    await tester.enterText(
      find.byWidgetPredicate(
        (widget) =>
            widget is TextField && widget.decoration?.labelText == 'Trip brief',
      ),
      'April trip',
    );
    await tester.tap(find.widgetWithText(FilledButton, 'Use this trip brief'));
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(OutlinedButton, 'Search'));
    await tester.pumpAndSettle();

    final monthField = find.byWidgetPredicate(
      (widget) =>
          widget is DropdownButtonFormField<int?> &&
          widget.decoration.labelText == 'Travel month (optional)',
    );
    await tester.ensureVisible(monthField);
    await tester.tap(monthField);
    await tester.pumpAndSettle();
    await tester.tap(find.text('May').last);
    await tester.pumpAndSettle();

    final save = find.widgetWithText(FilledButton, 'Save as current trip');
    await tester.ensureVisible(save);
    await tester.tap(save);
    await tester.pumpAndSettle();

    expect(savedBody, containsPair('travel_month', null));
    expect(savedBody, containsPair('trip_start_date', '2026-04-09'));
    expect(savedBody, containsPair('trip_end_date', '2026-04-16'));
  });

  testWidgets(
    'late brief and search responses do not update a disposed screen',
    (tester) async {
      final briefResponse = Completer<http.Response>();
      final searchResponse = Completer<http.Response>();
      final api = MobileApiClient(
        baseUrl: 'http://localhost/api',
        client: MockClient((request) {
          if (request.url.path == '/api/parse-query') {
            return briefResponse.future;
          }
          if (request.url.path == '/api/search') {
            return searchResponse.future;
          }
          return Future.value(http.Response('{}', 404));
        }),
      );
      final session = AppSession(
        accessToken: 'token',
        expiresAt: '2026-07-03T00:00:00Z',
        user: AppUser(userId: 'user-1', email: 'user@example.com'),
      );

      Widget screen() => MaterialApp(
        home: SearchScreen(
          api: api,
          session: session,
          authController: AuthController(
            api: api,
            sessionStore: InMemorySessionStore(),
          ),
        ),
      );

      await tester.pumpWidget(screen());
      await tester.enterText(
        find.byWidgetPredicate(
          (widget) =>
              widget is TextField &&
              widget.decoration?.labelText == 'Trip brief',
        ),
        'March trip',
      );
      await tester.tap(
        find.widgetWithText(FilledButton, 'Use this trip brief'),
      );
      await tester.pump();
      await tester.pumpWidget(const MaterialApp(home: SizedBox()));
      briefResponse.complete(
        http.Response('{"filters":{"travel_month":3}}', 200),
      );
      await tester.pump();
      expect(tester.takeException(), isNull);

      await tester.pumpWidget(screen());
      await tester.tap(find.widgetWithText(OutlinedButton, 'Search'));
      await tester.pump();
      await tester.pumpWidget(const MaterialApp(home: SizedBox()));
      searchResponse.complete(
        http.Response(jsonEncode(searchResponseJson()), 200),
      );
      await tester.pump();
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('late trip save does not update a disposed card', (tester) async {
    final saveResponse = Completer<http.Response>();
    final api = MobileApiClient(
      baseUrl: 'http://localhost/api',
      client: MockClient((request) => saveResponse.future),
    );
    final group = RecommendationGroupItem.fromJson(recommendationGroupJson());
    final session = AppSession(
      accessToken: 'token',
      expiresAt: '2026-07-03T00:00:00Z',
      user: AppUser(userId: 'user-1', email: 'user@example.com'),
    );

    await tester.pumpWidget(
      MaterialApp(
        home: RecommendationGroupCard(
          result: group,
          session: session,
          api: api,
          authController: AuthController(
            api: api,
            sessionStore: InMemorySessionStore(),
          ),
          travelWindow: const AppliedTravelWindow(month: 3),
        ),
      ),
    );
    await tester.tap(find.widgetWithText(FilledButton, 'Save as current trip'));
    await tester.pump();
    await tester.pumpWidget(const MaterialApp(home: SizedBox()));
    saveResponse.complete(http.Response('{}', 200));
    await tester.pump();

    expect(tester.takeException(), isNull);
  });

  test('parsed filters read exact date fields', () {
    final filters = ParsedFilters.fromJson({
      'location': 'France',
      'travel_month': 4,
      'trip_start_date': '2026-04-09',
      'trip_end_date': '2026-04-16',
    });

    expect(filters.location, 'France');
    expect(filters.travelMonth, 4);
    expect(filters.tripStartDate, '2026-04-09');
    expect(filters.tripEndDate, '2026-04-16');
  });

  test('mobile pass model preserves terrain scope and trust', () {
    final pass = RecommendationGroupItem.fromJson(
      recommendationGroupJson(),
    ).topConfiguration.selectedPass;

    expect(pass.accessiblePisteKmEvidence?.scope, PisteKmScope.pass);
    expect(
      pass.accessiblePisteKmEvidence?.trustStatus,
      CatalogTrustStatus.verified,
    );
  });

  test('mobile pass terrain copy stays scope-aware and trust-aware', () {
    String terrainCopy({String? scope, String? trustStatus}) {
      return PassOptionItem.fromJson({
        'lift_pass_product_id': 'test-pass',
        'name': 'Test pass',
        'accessible_piste_km': 120,
        if (scope != null && trustStatus != null)
          'accessible_piste_km_evidence': {
            'scope': scope,
            'trust_status': trustStatus,
          },
      }).terrainDescription;
    }

    expect(
      terrainCopy(
        scope: 'terrain_domain',
        trustStatus: 'verified_with_adjustment',
      ),
      'About 120.0 km of terrain in the pass-accessible area',
    );
    expect(
      terrainCopy(scope: 'pass', trustStatus: 'needs_source'),
      '120.0 km of terrain covered by this pass; source confirmation is still needed',
    );
    expect(terrainCopy(), '120.0 km reported; terrain scope is not confirmed');
  });

  testWidgets('mobile card renders V4 trip configuration', (tester) async {
    final group = RecommendationGroupItem.fromJson(recommendationGroupJson());
    final session = AppSession(
      accessToken: 'token',
      expiresAt: '2026-07-03T00:00:00+00:00',
      user: AppUser(userId: 'user-1', email: 'user@example.com'),
    );

    final api = MobileApiClient(baseUrl: 'http://localhost/api');
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: RecommendationGroupCard(
            result: group,
            session: session,
            api: api,
            authController: AuthController(
              api: api,
              sessionStore: InMemorySessionStore(),
            ),
            travelWindow: const AppliedTravelWindow(month: 3),
          ),
        ),
      ),
    );

    expect(find.text('Chamonix Valley'), findsOneWidget);
    expect(
      find.text('Trip option: stay in Argentiere and ski Grands Montets.'),
      findsOneWidget,
    );
    expect(find.text('Chamonix Le Pass'), findsOneWidget);
    expect(find.text('84.0 fit / 100'), findsNothing);
    expect(
      find.text('115.0 km of terrain covered by this pass'),
      findsOneWidget,
    );
    expect(find.text('Save as current trip'), findsOneWidget);
  });

  testWidgets(
    'mobile card does not present estimated ski-area terrain as pass terrain',
    (tester) async {
      final payload = recommendationGroupJson();
      final top = payload['top_configuration'] as Map<String, dynamic>;
      final selectedPass = top['selected_pass'] as Map<String, dynamic>;
      selectedPass['accessible_piste_km_evidence'] = {
        'trust_status': 'estimated',
        'scope': 'ski_area',
        'source_entity_id': 'grands-montets',
        'field_group': 'terrain_metrics',
      };
      final group = RecommendationGroupItem.fromJson(payload);
      final session = AppSession(
        accessToken: 'token',
        expiresAt: '2026-07-03T00:00:00+00:00',
        user: AppUser(userId: 'user-1', email: 'user@example.com'),
      );
      final api = MobileApiClient(baseUrl: 'http://localhost/api');

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: RecommendationGroupCard(
              result: group,
              session: session,
              api: api,
              authController: AuthController(
                api: api,
                sessionStore: InMemorySessionStore(),
              ),
              travelWindow: const AppliedTravelWindow(month: 3),
            ),
          ),
        ),
      );

      expect(
        find.text(
          'Estimated 115.0 km of terrain in the ski area; pass coverage is not confirmed',
        ),
        findsOneWidget,
      );
      expect(find.textContaining('km of pass terrain'), findsNothing);
    },
  );

  testWidgets('mobile search uses public vocabulary without debug terms', (
    tester,
  ) async {
    final api = MobileApiClient(baseUrl: 'http://localhost/api');
    final session = AppSession(
      accessToken: 'token',
      expiresAt: '2026-07-03T00:00:00Z',
      user: AppUser(userId: 'user-1', email: 'user@example.com'),
    );

    await tester.pumpWidget(
      MaterialApp(
        home: SearchScreen(
          api: api,
          session: session,
          authController: AuthController(
            api: api,
            sessionStore: InMemorySessionStore(),
          ),
        ),
      ),
    );

    expect(find.text('Must-haves and Preferences'), findsOneWidget);
    expect(find.text('Use this trip brief'), findsOneWidget);
    expect(find.text('Country'), findsOneWidget);
    expect(find.text('Maximum stay price per night (EUR)'), findsOneWidget);
    expect(find.text('Country / location'), findsNothing);
    expect(find.text('Maximum nightly lodging estimate'), findsNothing);
    expect(find.text('Stay comfort'), findsOneWidget);
    expect(find.text('Simple'), findsOneWidget);
    expect(find.text('Choose start date'), findsOneWidget);
    expect(find.text('Choose end date'), findsOneWidget);
    expect(find.textContaining('YYYY-MM-DD'), findsNothing);
    expect(find.textContaining('Quality tier'), findsNothing);
    expect(find.textContaining('API base:'), findsNothing);
    expect(find.textContaining('configuration'), findsNothing);
    expect(find.textContaining('ranking'), findsNothing);
    expect(find.textContaining('companion'), findsNothing);

    final tripBrief = find.byWidgetPredicate(
      (widget) =>
          widget is TextField && widget.decoration?.labelText == 'Trip brief',
    );
    expect(find.bySemanticsLabel('Trip brief'), findsOneWidget);
    await tester.enterText(tripBrief, 'March in France');
    expect(find.bySemanticsLabel('Trip brief'), findsOneWidget);
  });

  testWidgets('mobile search controls reflow at enlarged text scale', (
    tester,
  ) async {
    final api = MobileApiClient(baseUrl: 'http://localhost/api');
    final session = AppSession(
      accessToken: 'token',
      expiresAt: '2026-07-03T00:00:00Z',
      user: AppUser(userId: 'user-1', email: 'user@example.com'),
    );

    await tester.pumpWidget(
      MaterialApp(
        home: MediaQuery(
          data: const MediaQueryData(
            size: Size(320, 700),
            textScaler: TextScaler.linear(2),
          ),
          child: SearchScreen(
            api: api,
            session: session,
            authController: AuthController(
              api: api,
              sessionStore: InMemorySessionStore(),
            ),
          ),
        ),
      ),
    );

    expect(tester.takeException(), isNull);
    expect(
      tester
          .getSize(find.widgetWithText(FilledButton, 'Use this trip brief'))
          .height,
      greaterThanOrEqualTo(48),
    );
    await tester.drag(find.byType(ListView), const Offset(0, -1200));
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
    expect(find.text('Choose start date'), findsOneWidget);
    expect(
      tester
          .getSize(find.widgetWithText(OutlinedButton, 'Choose start date'))
          .height,
      greaterThanOrEqualTo(48),
    );
  });

  test('saving a mobile trip sends every normalized V4 identity', () async {
    late Map<String, dynamic> requestBody;
    final api = MobileApiClient(
      baseUrl: 'http://localhost/api',
      client: MockClient((request) async {
        requestBody = jsonDecode(request.body) as Map<String, dynamic>;
        return http.Response('{}', 200);
      }),
    );
    final group = RecommendationGroupItem.fromJson(recommendationGroupJson());

    await api.saveCurrentTrip(token: 'token', result: group, travelMonth: 3);

    expect(requestBody, containsPair('ski_region_id', 'chamonix-valley'));
    expect(
      requestBody,
      containsPair('stay_destination_id', 'chamonix-mont-blanc'),
    );
    expect(
      requestBody,
      containsPair('stay_base_id', 'chamonix-mont-blanc-argentiere'),
    );
    expect(requestBody, containsPair('focus_ski_area_id', 'grands-montets'));
    expect(
      requestBody,
      containsPair('lift_pass_product_id', 'chamonix-le-pass'),
    );
  });
}
