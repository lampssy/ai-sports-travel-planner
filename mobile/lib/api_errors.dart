import 'dart:convert';

enum PublicApiErrorCode {
  invalidRequest,
  authenticationRequired,
  sessionExpired,
  signInFailed,
  signInUnavailable,
  searchRequestInvalid,
  weatherAreaNotFound,
  refinementRateLimited,
  tripOptionInvalid,
  currentTripNotFound,
  notFound,
  methodNotAllowed,
  requestFailed,
}

enum ApiFailureKind { response, transport, decode }

enum ApiOperation {
  signIn,
  parseTripBrief,
  search,
  currentTripSave,
  currentTripSummary,
  currentTripEvents,
  currentTripMarkChecked,
}

const _publicCodeByValue = <String, PublicApiErrorCode>{
  'invalid_request': PublicApiErrorCode.invalidRequest,
  'authentication_required': PublicApiErrorCode.authenticationRequired,
  'session_expired': PublicApiErrorCode.sessionExpired,
  'sign_in_failed': PublicApiErrorCode.signInFailed,
  'sign_in_unavailable': PublicApiErrorCode.signInUnavailable,
  'search_request_invalid': PublicApiErrorCode.searchRequestInvalid,
  'weather_area_not_found': PublicApiErrorCode.weatherAreaNotFound,
  'refinement_rate_limited': PublicApiErrorCode.refinementRateLimited,
  'trip_option_invalid': PublicApiErrorCode.tripOptionInvalid,
  'current_trip_not_found': PublicApiErrorCode.currentTripNotFound,
  'not_found': PublicApiErrorCode.notFound,
  'method_not_allowed': PublicApiErrorCode.methodNotAllowed,
  'request_failed': PublicApiErrorCode.requestFailed,
};

const _fallbackCopy = <ApiOperation, String>{
  ApiOperation.signIn: 'Sign-in could not be completed. Try again.',
  ApiOperation.parseTripBrief: 'Your trip brief could not be read. Try again.',
  ApiOperation.search: 'Trip options could not be loaded. Try again.',
  ApiOperation.currentTripSave: 'Your trip could not be saved. Try again.',
  ApiOperation.currentTripSummary:
      'Your current trip could not be loaded. Try again.',
  ApiOperation.currentTripEvents:
      'Trip updates could not be loaded. Try again.',
  ApiOperation.currentTripMarkChecked:
      'Your current trip could not be updated. Try again.',
};

class PublicApiException implements Exception {
  const PublicApiException._({required this.kind, this.code});

  factory PublicApiException.response(String body) => PublicApiException._(
    kind: ApiFailureKind.response,
    code: publicErrorCodeFromBody(body),
  );

  factory PublicApiException.transport([Object? _]) =>
      const PublicApiException._(kind: ApiFailureKind.transport);

  factory PublicApiException.decode([Object? _]) =>
      const PublicApiException._(kind: ApiFailureKind.decode);

  final ApiFailureKind kind;
  final PublicApiErrorCode? code;
}

PublicApiErrorCode? publicErrorCodeFromBody(String body) {
  try {
    final payload = jsonDecode(body);
    if (payload is! Map<String, dynamic> ||
        payload.length != 1 ||
        !payload.containsKey('error')) {
      return null;
    }
    final error = payload['error'];
    if (error is! Map<String, dynamic> ||
        error.length != 1 ||
        !error.containsKey('code')) {
      return null;
    }
    final code = error['code'];
    return code is String ? _publicCodeByValue[code] : null;
  } on FormatException {
    return null;
  }
}

String apiErrorMessage(ApiOperation operation, PublicApiException failure) {
  final code = failure.code;
  if (code == PublicApiErrorCode.authenticationRequired ||
      code == PublicApiErrorCode.sessionExpired) {
    return 'Sign in to continue.';
  }
  if (operation == ApiOperation.signIn) {
    if (code == PublicApiErrorCode.signInUnavailable) {
      return 'Sign-in is temporarily unavailable. Try again later.';
    }
    return _fallbackCopy[operation]!;
  }
  if (operation == ApiOperation.currentTripSave &&
      code == PublicApiErrorCode.tripOptionInvalid) {
    return 'This trip option could not be saved. Return to the results and '
        'choose the trip option again.';
  }
  if (code == PublicApiErrorCode.currentTripNotFound) {
    return 'No current trip is saved.';
  }
  if ((operation == ApiOperation.search ||
          operation == ApiOperation.parseTripBrief) &&
      (code == PublicApiErrorCode.invalidRequest ||
          code == PublicApiErrorCode.searchRequestInvalid)) {
    return operation == ApiOperation.search
        ? 'Review your trip choices and try again.'
        : 'Your trip brief could not be read. Review it and try again.';
  }
  if (failure.kind == ApiFailureKind.transport &&
      operation == ApiOperation.search) {
    return 'Trip options could not be loaded. Check your connection and try again.';
  }
  if (failure.kind == ApiFailureKind.transport &&
      operation == ApiOperation.parseTripBrief) {
    return 'Your trip brief could not be read. Check your connection and try again.';
  }
  return _fallbackCopy[operation]!;
}
