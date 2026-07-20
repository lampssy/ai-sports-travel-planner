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

Map<String, dynamic> searchResponseJson() => {
  'search_model_version': 'search-v4',
  'ranking_policy_version': 'search-v4-policy-1',
  'ranking_status': 'ranked',
  'unscored_reason': null,
  'applied_intent': <String, dynamic>{},
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
            travelMonth: 3,
            tripStartDate: '',
            tripEndDate: '',
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
    expect(find.text('115.0 km of pass terrain'), findsOneWidget);
    expect(find.text('Save as current trip'), findsOneWidget);
  });

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
