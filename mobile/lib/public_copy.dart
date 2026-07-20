class PublicCopy {
  const PublicCopy._();

  static const appName = 'Snowcast';
  static const signInHeading = 'Sign in to Snowcast';
  static const sessionEnded = 'Your session ended. Sign in again.';
  static const signInRequired = 'Sign in to continue.';
  static const tripOptions = 'Trip options';
  static const tripOption = 'Trip option';
  static const tripDetails = 'Trip details';
  static const mustHaves = 'Must-haves';
  static const preferences = 'Preferences';
  static const currentTrip = 'Current trip';
  static const tripUpdates = 'Trip updates';

  static const monthNames = <String>[
    'January',
    'February',
    'March',
    'April',
    'May',
    'June',
    'July',
    'August',
    'September',
    'October',
    'November',
    'December',
  ];

  static const qualityLabels = <int, String>{
    1: 'Simple',
    2: 'Comfortable',
    3: 'Premium',
  };
}

String formatPublicDate(String value) {
  final date = DateTime.tryParse(value)?.toLocal();
  if (date == null) {
    return 'Date unavailable';
  }
  return '${PublicCopy.monthNames[date.month - 1]} ${date.day}, ${date.year}';
}

String formatPublicDateRange(String start, String end) {
  return '${formatPublicDate(start)} to ${formatPublicDate(end)}';
}
