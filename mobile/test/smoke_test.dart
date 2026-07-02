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
  'score': 0.84,
  'top_configuration': {
    'configuration_id': 'chamonix|argentiere|grands-montets',
    'ski_region_id': 'chamonix-valley',
    'stay_destination_id': 'chamonix-mont-blanc',
    'stay_destination_name': 'Chamonix-Mont-Blanc',
    'stay_base_id': 'chamonix-mont-blanc-argentiere',
    'stay_base_name': 'Argentiere',
    'focus_ski_area_id': 'grands-montets',
    'focus_ski_area_name': 'Grands Montets',
    'access': {
      'ski_area_access_id': 'argentiere-grands-montets',
      'mode': 'walk',
      'lift_distance': 'near',
      'nearest_lift_name': 'Plan Joran',
      'distance_m': 450,
      'duration_minutes': 7,
      'is_direct': true,
    },
    'selected_pass': {
      'lift_pass_product_id': 'chamonix-le-pass',
      'name': 'Chamonix Le Pass',
      'validity_scope': 'multi_ski_area',
      'accessible_ski_area_ids': ['grands-montets'],
      'accessible_terrain_label': 'Chamonix Le Pass terrain',
      'accessible_piste_km': 115,
      'price_example': null,
      'pass_fit_score': 0.9,
      'tradeoff_summary': 'Local Chamonix terrain coverage.',
    },
    'alternative_passes': [],
    'resilience': {
      'alternative_area_count': 2,
      'evidenced_alternative_count': 2,
      'areas': [],
      'summary': 'Two fallback areas are available.',
      'ranking_component': 0,
    },
    'score': 0.84,
    'score_components': <String, double>{},
    'budget_penalty': 0,
    'travel_effort': null,
    'conditions_summary': 'Good selected-area snow evidence.',
    'snow_confidence_score': 0.82,
    'conditions_score': 0.8,
    'planning_summary': 'Archive-backed March outlook.',
    'planning_provenance': null,
    'planning_evidence_count': 12,
    'planning_weather_metrics': {'evidence_years': 12},
    'evidence_quality': <String, dynamic>{},
    'explanation': <String, dynamic>{},
  },
  'alternative_configurations': <Map<String, dynamic>>[],
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

    expect(find.text('Snowcast Mobile'), findsOneWidget);
    expect(find.text('Sign in with Google'), findsOneWidget);
  });

  test('mobile search sends exact dates instead of travel month', () async {
    Uri? requestedUrl;
    final api = MobileApiClient(
      baseUrl: 'http://localhost/api',
      client: MockClient((request) async {
        requestedUrl = request.url;
        return http.Response(jsonEncode({'results': []}), 200);
      }),
    );

    await api.search(
      location: 'France',
      minPrice: 150,
      maxPrice: 320,
      stars: 2,
      skillLevel: 'intermediate',
      travelMonth: 3,
      tripStartDate: '2026-04-09',
      tripEndDate: '2026-04-16',
    );

    expect(requestedUrl, isNotNull);
    expect(requestedUrl!.queryParameters['trip_start_date'], '2026-04-09');
    expect(requestedUrl!.queryParameters['trip_end_date'], '2026-04-16');
    expect(requestedUrl!.queryParameters.containsKey('travel_month'), isFalse);
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

  testWidgets('mobile card renders normalized trip configuration', (
    tester,
  ) async {
    final group = RecommendationGroupItem.fromJson(recommendationGroupJson());
    final session = AppSession(
      accessToken: 'token',
      expiresAt: '2026-07-03T00:00:00+00:00',
      user: AppUser(userId: 'user-1', email: 'user@example.com'),
    );

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: RecommendationGroupCard(
            result: group,
            session: session,
            api: MobileApiClient(baseUrl: 'http://localhost/api'),
            travelMonth: 3,
            tripStartDate: '',
            tripEndDate: '',
          ),
        ),
      ),
    );

    expect(find.text('Chamonix Valley'), findsOneWidget);
    expect(
      find.text('Stay in Argentiere - Ski Grands Montets'),
      findsOneWidget,
    );
    expect(find.text('Chamonix Le Pass'), findsOneWidget);
    expect(find.text('Archive-backed March outlook.'), findsOneWidget);
  });

  test('saving a mobile trip sends every normalized identity', () async {
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
