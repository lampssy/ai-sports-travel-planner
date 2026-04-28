import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:snowcast_mobile/main.dart';

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
}
