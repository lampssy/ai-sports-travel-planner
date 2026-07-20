import 'package:flutter_test/flutter_test.dart';
import 'package:snowcast_mobile/api_errors.dart';

void main() {
  group('public API error parsing', () {
    test('accepts a known code in the exact public envelope', () {
      expect(
        publicErrorCodeFromBody('{"error":{"code":"session_expired"}}'),
        PublicApiErrorCode.sessionExpired,
      );
    });

    test('rejects unknown codes', () {
      expect(
        publicErrorCodeFromBody('{"error":{"code":"provider_timeout"}}'),
        isNull,
      );
    });

    test('rejects absent, malformed, non-JSON, and extended envelopes', () {
      expect(publicErrorCodeFromBody('{}'), isNull);
      expect(publicErrorCodeFromBody('{"error":'), isNull);
      expect(publicErrorCodeFromBody('upstream /private/path failed'), isNull);
      expect(
        publicErrorCodeFromBody(
          '{"error":{"code":"request_failed","detail":"secret"}}',
        ),
        isNull,
      );
      expect(
        publicErrorCodeFromBody(
          '{"error":{"code":"request_failed"},"request_id":"internal"}',
        ),
        isNull,
      );
    });
  });

  group('operation-specific public copy', () {
    test('maps known response codes without exposing the response body', () {
      const raw = 'Provider failed at /srv/private.py with bearer secret-token';
      final knownFailure = PublicApiException.response(
        '{"error":{"code":"trip_option_invalid"}}',
      );
      final extendedFailure = PublicApiException.response(
        '{"error":{"code":"trip_option_invalid"},"detail":"$raw"}',
      );

      final knownMessage = apiErrorMessage(
        ApiOperation.currentTripSave,
        knownFailure,
      );
      final fallbackMessage = apiErrorMessage(
        ApiOperation.currentTripSave,
        extendedFailure,
      );

      expect(knownMessage, contains('choose the trip option again'));
      expect(fallbackMessage, 'Your trip could not be saved. Try again.');
      expect(fallbackMessage, isNot(contains(raw)));
      expect(fallbackMessage, isNot(contains('/srv/private.py')));
      expect(fallbackMessage, isNot(contains('secret-token')));
    });

    test(
      'uses safe operation fallbacks for unknown and malformed responses',
      () {
        final unknown = PublicApiException.response(
          '{"error":{"code":"provider_timeout"}}',
        );
        final malformed = PublicApiException.response(
          '<html>proxy at /internal/path</html>',
        );

        expect(
          apiErrorMessage(ApiOperation.currentTripEvents, unknown),
          'Trip updates could not be loaded. Try again.',
        );
        expect(
          apiErrorMessage(ApiOperation.currentTripSummary, malformed),
          'Your current trip could not be loaded. Try again.',
        );
      },
    );

    test('maps transport and success-decoding failures without raw details', () {
      final transport = PublicApiException.transport(
        StateError('Socket failed for https://private-host'),
      );
      final decode = PublicApiException.decode(
        const FormatException('Unexpected token at byte 42'),
      );

      final transportMessage = apiErrorMessage(ApiOperation.search, transport);
      final decodeMessage = apiErrorMessage(
        ApiOperation.currentTripEvents,
        decode,
      );

      expect(
        transportMessage,
        'Trip options could not be loaded. Check your connection and try again.',
      );
      expect(decodeMessage, 'Trip updates could not be loaded. Try again.');
      expect(transportMessage, isNot(contains('private-host')));
      expect(decodeMessage, isNot(contains('byte 42')));
    });
  });
}
