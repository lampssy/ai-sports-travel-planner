import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

const _apiBaseUrl = String.fromEnvironment(
  'API_BASE_URL',
  defaultValue: 'http://10.0.2.2:8000/api',
);
const _googleServerClientId = String.fromEnvironment(
  'GOOGLE_SERVER_CLIENT_ID',
  defaultValue: '',
);

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final sessionStore = SharedPreferencesSessionStore(SharedPreferencesAsync());
  final api = MobileApiClient(baseUrl: _apiBaseUrl);
  final authController = AuthController(api: api, sessionStore: sessionStore);
  await authController.restoreSession();
  runApp(SnowcastApp(api: api, authController: authController));
}

class SnowcastApp extends StatelessWidget {
  const SnowcastApp({
    super.key,
    MobileApiClient? api,
    AuthController? authController,
  })  : _api = api,
        _authController = authController;

  final MobileApiClient? _api;
  final AuthController? _authController;

  @override
  Widget build(BuildContext context) {
    final api = _api ?? MobileApiClient(baseUrl: _apiBaseUrl);
    final authController = _authController ??
        AuthController(
          api: api,
          sessionStore: SharedPreferencesSessionStore(SharedPreferencesAsync()),
        );

    return MaterialApp(
      title: 'Snowcast Mobile',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF0F766E)),
        useMaterial3: true,
      ),
      home: AnimatedBuilder(
        animation: authController,
        builder: (context, _) {
          if (authController.isBusy) {
            return const Scaffold(
              body: Center(child: CircularProgressIndicator()),
            );
          }
          if (authController.session == null) {
            return SignInScreen(authController: authController);
          }
          return MobileShell(
            api: api,
            authController: authController,
          );
        },
      ),
    );
  }
}

class AuthController extends ChangeNotifier {
  AuthController({
    required this.api,
    required this.sessionStore,
  });

  final MobileApiClient api;
  final SessionStore sessionStore;

  AppSession? session;
  bool isBusy = false;
  bool _googleInitialized = false;
  String? errorMessage;

  Future<void> restoreSession() async {
    session = await sessionStore.read();
    notifyListeners();
  }

  Future<void> signInWithGoogle() async {
    isBusy = true;
    errorMessage = null;
    notifyListeners();

    try {
      await _ensureGoogleInitialized();
      final account = await GoogleSignIn.instance.authenticate();
      final authentication = account.authentication;
      final identityToken = authentication.idToken;
      if (identityToken == null || identityToken.isEmpty) {
        throw const MobileApiException(
          'Google sign-in did not return an identity token.',
        );
      }

      final newSession = await api.exchangeGoogleIdentityToken(identityToken);
      await sessionStore.write(newSession);
      session = newSession;
    } on GoogleSignInException catch (error) {
      errorMessage = error.description ?? error.code.name;
    } on MobileApiException catch (error) {
      errorMessage = error.message;
    } finally {
      isBusy = false;
      notifyListeners();
    }
  }

  Future<void> signOut() async {
    await GoogleSignIn.instance.signOut();
    await sessionStore.clear();
    session = null;
    errorMessage = null;
    notifyListeners();
  }

  Future<void> _ensureGoogleInitialized() async {
    if (_googleInitialized) {
      return;
    }
    await GoogleSignIn.instance.initialize(
      serverClientId:
          _googleServerClientId.isEmpty ? null : _googleServerClientId,
    );
    final attempt = GoogleSignIn.instance.attemptLightweightAuthentication();
    if (attempt != null) {
      unawaited(attempt);
    }
    _googleInitialized = true;
  }
}

class SignInScreen extends StatelessWidget {
  const SignInScreen({super.key, required this.authController});

  final AuthController authController;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 420),
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Card(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Snowcast Mobile',
                      style: Theme.of(context).textTheme.headlineMedium,
                    ),
                    const SizedBox(height: 12),
                    const Text(
                      'Sign in with Google to keep one current trip attached to your account and use the mobile planning flow.',
                    ),
                    const SizedBox(height: 24),
                    FilledButton.icon(
                      onPressed: authController.isBusy
                          ? null
                          : authController.signInWithGoogle,
                      icon: const Icon(Icons.login),
                      label: const Text('Sign in with Google'),
                    ),
                    if (authController.errorMessage != null) ...[
                      const SizedBox(height: 12),
                      Text(
                        authController.errorMessage!,
                        style: TextStyle(
                          color: Theme.of(context).colorScheme.error,
                        ),
                      ),
                    ],
                    const SizedBox(height: 16),
                    Text(
                      'API base: $_apiBaseUrl',
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class MobileShell extends StatefulWidget {
  const MobileShell({
    super.key,
    required this.api,
    required this.authController,
  });

  final MobileApiClient api;
  final AuthController authController;

  @override
  State<MobileShell> createState() => _MobileShellState();
}

class _MobileShellState extends State<MobileShell> {
  int _selectedIndex = 0;

  @override
  Widget build(BuildContext context) {
    final session = widget.authController.session!;
    final pages = [
      SearchScreen(api: widget.api, session: session),
      CurrentTripScreen(api: widget.api, session: session),
    ];

    return Scaffold(
      appBar: AppBar(
        title: Text(_selectedIndex == 0 ? 'Plan trip' : 'Current trip'),
        actions: [
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12),
            child: Center(child: Text(session.user.email)),
          ),
          IconButton(
            onPressed: widget.authController.signOut,
            icon: const Icon(Icons.logout),
            tooltip: 'Sign out',
          ),
        ],
      ),
      body: pages[_selectedIndex],
      bottomNavigationBar: NavigationBar(
        selectedIndex: _selectedIndex,
        onDestinationSelected: (index) {
          setState(() {
            _selectedIndex = index;
          });
        },
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.search),
            label: 'Search',
          ),
          NavigationDestination(
            icon: Icon(Icons.downhill_skiing),
            label: 'Current trip',
          ),
        ],
      ),
    );
  }
}

class SearchScreen extends StatefulWidget {
  const SearchScreen({
    super.key,
    required this.api,
    required this.session,
  });

  final MobileApiClient api;
  final AppSession session;

  @override
  State<SearchScreen> createState() => _SearchScreenState();
}

class _SearchScreenState extends State<SearchScreen> {
  final _briefController = TextEditingController();
  final _locationController = TextEditingController(text: 'France');
  final _minPriceController = TextEditingController(text: '150');
  final _maxPriceController = TextEditingController(text: '320');
  final _travelMonthController = TextEditingController(text: '3');

  String _skillLevel = 'intermediate';
  int _stars = 1;
  bool _isBusy = false;
  String? _errorMessage;
  List<SearchResultItem> _results = const [];

  @override
  void dispose() {
    _briefController.dispose();
    _locationController.dispose();
    _minPriceController.dispose();
    _maxPriceController.dispose();
    _travelMonthController.dispose();
    super.dispose();
  }

  Future<void> _parseBrief() async {
    if (_briefController.text.trim().isEmpty) {
      return;
    }

    setState(() {
      _isBusy = true;
      _errorMessage = null;
    });

    try {
      final parsed = await widget.api.parseTripBrief(_briefController.text.trim());
      _locationController.text = parsed.location ?? _locationController.text;
      if (parsed.minPrice != null) {
        _minPriceController.text = parsed.minPrice!.toStringAsFixed(0);
      }
      if (parsed.maxPrice != null) {
        _maxPriceController.text = parsed.maxPrice!.toStringAsFixed(0);
      }
      if (parsed.travelMonth != null) {
        _travelMonthController.text = parsed.travelMonth!.toString();
      }
      if (parsed.skillLevel != null) {
        _skillLevel = parsed.skillLevel!;
      }
    } on MobileApiException catch (error) {
      _errorMessage = error.message;
    } finally {
      setState(() {
        _isBusy = false;
      });
    }
  }

  Future<void> _runSearch() async {
    setState(() {
      _isBusy = true;
      _errorMessage = null;
    });

    try {
      final results = await widget.api.search(
        location: _locationController.text.trim(),
        minPrice: double.parse(_minPriceController.text),
        maxPrice: double.parse(_maxPriceController.text),
        stars: _stars,
        skillLevel: _skillLevel,
        travelMonth: int.tryParse(_travelMonthController.text.trim()),
      );
      setState(() {
        _results = results;
      });
    } on FormatException {
      setState(() {
        _errorMessage = 'Prices must be valid numbers.';
      });
    } on MobileApiException catch (error) {
      setState(() {
        _errorMessage = error.message;
      });
    } finally {
      setState(() {
        _isBusy = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Trip brief',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: 8),
                TextField(
                  controller: _briefController,
                  minLines: 2,
                  maxLines: 3,
                  decoration: const InputDecoration(
                    hintText:
                        'Cheap March ski trip in France for intermediates, close to the lift.',
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 12),
                Wrap(
                  spacing: 12,
                  runSpacing: 12,
                  children: [
                    FilledButton(
                      onPressed: _isBusy ? null : _parseBrief,
                      child: const Text('Parse brief'),
                    ),
                    OutlinedButton(
                      onPressed: _isBusy ? null : _runSearch,
                      child: const Text('Search'),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                Text(
                  'Structured filters',
                  style: Theme.of(context).textTheme.titleSmall,
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: _locationController,
                  decoration: const InputDecoration(
                    labelText: 'Country / location',
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: _minPriceController,
                        keyboardType: TextInputType.number,
                        decoration: const InputDecoration(
                          labelText: 'Min price',
                          border: OutlineInputBorder(),
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: TextField(
                        controller: _maxPriceController,
                        keyboardType: TextInputType.number,
                        decoration: const InputDecoration(
                          labelText: 'Max price',
                          border: OutlineInputBorder(),
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                DropdownButtonFormField<int>(
                  initialValue: _stars,
                  decoration: const InputDecoration(
                    labelText: 'Quality tier',
                    border: OutlineInputBorder(),
                  ),
                  items: const [
                    DropdownMenuItem(value: 1, child: Text('1')),
                    DropdownMenuItem(value: 2, child: Text('2')),
                    DropdownMenuItem(value: 3, child: Text('3')),
                  ],
                  onChanged: (value) {
                    setState(() {
                      _stars = value ?? 1;
                    });
                  },
                ),
                const SizedBox(height: 12),
                DropdownButtonFormField<String>(
                  initialValue: _skillLevel,
                  decoration: const InputDecoration(
                    labelText: 'Skill level',
                    border: OutlineInputBorder(),
                  ),
                  items: const [
                    DropdownMenuItem(
                      value: 'beginner',
                      child: Text('Beginner'),
                    ),
                    DropdownMenuItem(
                      value: 'intermediate',
                      child: Text('Intermediate'),
                    ),
                    DropdownMenuItem(
                      value: 'advanced',
                      child: Text('Advanced'),
                    ),
                  ],
                  onChanged: (value) {
                    setState(() {
                      _skillLevel = value ?? 'intermediate';
                    });
                  },
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: _travelMonthController,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(
                    labelText: 'Travel month (optional)',
                    border: OutlineInputBorder(),
                  ),
                ),
                if (_errorMessage != null) ...[
                  const SizedBox(height: 12),
                  Text(
                    _errorMessage!,
                    style: TextStyle(
                      color: Theme.of(context).colorScheme.error,
                    ),
                  ),
                ],
              ],
            ),
          ),
        ),
        const SizedBox(height: 16),
        if (_isBusy) const LinearProgressIndicator(),
        if (_results.isEmpty && !_isBusy)
          const Padding(
            padding: EdgeInsets.all(12),
            child: Text('Run a search to load mobile planning results.'),
          ),
        for (final result in _results)
          SearchResultCard(
            result: result,
            session: widget.session,
            api: widget.api,
          ),
      ],
    );
  }
}

class SearchResultCard extends StatefulWidget {
  const SearchResultCard({
    super.key,
    required this.result,
    required this.session,
    required this.api,
  });

  final SearchResultItem result;
  final AppSession session;
  final MobileApiClient api;

  @override
  State<SearchResultCard> createState() => _SearchResultCardState();
}

class _SearchResultCardState extends State<SearchResultCard> {
  bool _saving = false;
  String? _message;

  Future<void> _saveCurrentTrip() async {
    setState(() {
      _saving = true;
      _message = null;
    });

    try {
      await widget.api.saveCurrentTrip(
        token: widget.session.accessToken,
        result: widget.result,
      );
      setState(() {
        _message = 'Saved as current trip.';
      });
    } on MobileApiException catch (error) {
      setState(() {
        _message = error.message;
      });
    } finally {
      setState(() {
        _saving = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final result = widget.result;
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(result.resortName, style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 8),
            Text(result.conditionsSummary),
            if (result.planningSummary != null) ...[
              const SizedBox(height: 8),
              Text(result.planningSummary!),
            ],
            if (result.recommendationNarrative != null) ...[
              const SizedBox(height: 8),
              Text(
                result.recommendationNarrative!,
                style: Theme.of(context).textTheme.bodyMedium,
              ),
            ],
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                Chip(label: Text(result.selectedSkiAreaName)),
                Chip(label: Text(result.selectedStayBaseName)),
                Chip(label: Text(result.snowConfidenceLabel)),
                Chip(label: Text(result.availabilityStatus.replaceAll('_', ' '))),
              ],
            ),
            const SizedBox(height: 12),
            FilledButton(
              onPressed: _saving ? null : _saveCurrentTrip,
              child: Text(_saving ? 'Saving...' : 'Save current trip'),
            ),
            if (_message != null) ...[
              const SizedBox(height: 8),
              Text(_message!),
            ],
          ],
        ),
      ),
    );
  }
}

class CurrentTripScreen extends StatefulWidget {
  const CurrentTripScreen({
    super.key,
    required this.api,
    required this.session,
  });

  final MobileApiClient api;
  final AppSession session;

  @override
  State<CurrentTripScreen> createState() => _CurrentTripScreenState();
}

class _CurrentTripScreenState extends State<CurrentTripScreen> {
  bool _loading = true;
  String? _errorMessage;
  CurrentTripSummaryData? _summary;

  @override
  void initState() {
    super.initState();
    unawaited(_loadSummary());
  }

  Future<void> _loadSummary() async {
    setState(() {
      _loading = true;
      _errorMessage = null;
    });

    try {
      final summary = await widget.api.getCurrentTripSummary(
        token: widget.session.accessToken,
      );
      setState(() {
        _summary = summary;
      });
    } on MobileApiException catch (error) {
      setState(() {
        _errorMessage = error.message;
      });
    } finally {
      setState(() {
        _loading = false;
      });
    }
  }

  Future<void> _markChecked() async {
    try {
      await widget.api.markCurrentTripChecked(token: widget.session.accessToken);
      await _loadSummary();
    } on MobileApiException catch (error) {
      setState(() {
        _errorMessage = error.message;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_errorMessage != null) {
      return Center(child: Text(_errorMessage!));
    }
    if (_summary == null) {
      return RefreshIndicator(
        onRefresh: _loadSummary,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          children: const [
            SizedBox(height: 120),
            Center(child: Text('No current trip saved yet.')),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _loadSummary,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    _summary!.tripResortName,
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                  const SizedBox(height: 8),
                  Text(_summary!.selectedSkiAreaName),
                  Text(_summary!.selectedStayBaseName),
                  const SizedBox(height: 12),
                  Text(_summary!.currentWeatherSummary),
                  const SizedBox(height: 12),
                  Text('Comparison basis: ${_summary!.comparisonLabel}'),
                  Text(_summary!.deltaSummary),
                  const SizedBox(height: 12),
                  FilledButton(
                    onPressed: _markChecked,
                    child: const Text('Mark checked'),
                  ),
                ],
              ),
            ),
          ),
          if (_summary!.changes.isNotEmpty) ...[
            const SizedBox(height: 12),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Changes',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: 8),
                    for (final change in _summary!.changes)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 8),
                        child: Text('• $change'),
                      ),
                  ],
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class MobileApiClient {
  MobileApiClient({
    required this.baseUrl,
    http.Client? client,
  }) : _client = client ?? http.Client();

  final String baseUrl;
  final http.Client _client;

  Future<AppSession> exchangeGoogleIdentityToken(String identityToken) async {
    final response = await _client.post(
      Uri.parse('$baseUrl/auth/google/sign-in'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'identity_token': identityToken}),
    );
    final payload = await _decodeJsonMap(response);
    _ensureSuccess(response, payload);
    return AppSession.fromJson(payload);
  }

  Future<ParsedFilters> parseTripBrief(String query) async {
    final response = await _client.post(
      Uri.parse('$baseUrl/parse-query'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'query': query}),
    );
    final payload = await _decodeJsonMap(response);
    _ensureSuccess(response, payload);
    return ParsedFilters.fromJson(
      (payload['filters'] as Map<String, dynamic>? ?? const {}),
    );
  }

  Future<List<SearchResultItem>> search({
    required String location,
    required double minPrice,
    required double maxPrice,
    required int stars,
    required String skillLevel,
    int? travelMonth,
  }) async {
    final query = <String, String>{
      'location': location,
      'min_price': minPrice.toStringAsFixed(0),
      'max_price': maxPrice.toStringAsFixed(0),
      'stars': '$stars',
      'skill_level': skillLevel,
    };
    if (travelMonth != null) {
      query['travel_month'] = '$travelMonth';
    }

    final uri = Uri.parse('$baseUrl/search').replace(queryParameters: query);
    final response = await _client.get(uri);
    final payload = await _decodeJsonMap(response);
    _ensureSuccess(response, payload);
    final results = payload['results'] as List<dynamic>? ?? const [];
    return results
        .map((result) => SearchResultItem.fromJson(result as Map<String, dynamic>))
        .toList();
  }

  Future<void> saveCurrentTrip({
    required String token,
    required SearchResultItem result,
  }) async {
    final response = await _client.put(
      Uri.parse('$baseUrl/current-trip'),
      headers: _authorizedHeaders(token),
      body: jsonEncode({
        'resort_id': result.resortId,
        'selected_ski_area_name': result.selectedSkiAreaName,
        'selected_stay_base_name': result.selectedStayBaseName,
        'travel_month': result.travelMonth,
        'booking_status': 'not_booked_yet',
      }),
    );
    final payload = await _decodeJsonMap(response);
    _ensureSuccess(response, payload);
  }

  Future<CurrentTripSummaryData?> getCurrentTripSummary({
    required String token,
  }) async {
    final response = await _client.get(
      Uri.parse('$baseUrl/current-trip/summary'),
      headers: _authorizedHeaders(token, includeContentType: false),
    );
    if (response.statusCode == 404) {
      return null;
    }
    final payload = await _decodeJsonMap(response);
    _ensureSuccess(response, payload);
    return CurrentTripSummaryData.fromJson(payload);
  }

  Future<void> markCurrentTripChecked({required String token}) async {
    final response = await _client.post(
      Uri.parse('$baseUrl/current-trip/mark-checked'),
      headers: _authorizedHeaders(token, includeContentType: false),
    );
    final payload = await _decodeJsonMap(response);
    _ensureSuccess(response, payload);
  }

  Map<String, String> _authorizedHeaders(
    String token, {
    bool includeContentType = true,
  }) {
    return {
      if (includeContentType) 'Content-Type': 'application/json',
      'Authorization': 'Bearer $token',
    };
  }

  Future<Map<String, dynamic>> _decodeJsonMap(http.Response response) async {
    if (response.body.isEmpty) {
      return const {};
    }
    return jsonDecode(response.body) as Map<String, dynamic>;
  }

  void _ensureSuccess(http.Response response, Map<String, dynamic> payload) {
    if (response.statusCode < 400) {
      return;
    }
    throw MobileApiException(
      payload['detail'] as String? ?? 'Request failed with ${response.statusCode}.',
    );
  }
}

abstract class SessionStore {
  Future<void> write(AppSession session);
  Future<AppSession?> read();
  Future<void> clear();
}

class SharedPreferencesSessionStore implements SessionStore {
  const SharedPreferencesSessionStore(this._preferences);

  final SharedPreferencesAsync _preferences;

  static const _accessTokenKey = 'access_token';
  static const _expiresAtKey = 'expires_at';
  static const _userIdKey = 'user_id';
  static const _userEmailKey = 'user_email';
  static const _userDisplayNameKey = 'user_display_name';

  @override
  Future<void> write(AppSession session) async {
    await _preferences.setString(_accessTokenKey, session.accessToken);
    await _preferences.setString(_expiresAtKey, session.expiresAt);
    await _preferences.setString(_userIdKey, session.user.userId);
    await _preferences.setString(_userEmailKey, session.user.email);
    await _preferences.setString(
      _userDisplayNameKey,
      session.user.displayName ?? '',
    );
  }

  @override
  Future<AppSession?> read() async {
    final accessToken = await _preferences.getString(_accessTokenKey);
    if (accessToken == null || accessToken.isEmpty) {
      return null;
    }
    return AppSession(
      accessToken: accessToken,
      expiresAt: (await _preferences.getString(_expiresAtKey)) ?? '',
      user: AppUser(
        userId: (await _preferences.getString(_userIdKey)) ?? '',
        email: (await _preferences.getString(_userEmailKey)) ?? '',
        displayName: await _preferences.getString(_userDisplayNameKey),
      ),
    );
  }

  @override
  Future<void> clear() async {
    await _preferences.remove(_accessTokenKey);
    await _preferences.remove(_expiresAtKey);
    await _preferences.remove(_userIdKey);
    await _preferences.remove(_userEmailKey);
    await _preferences.remove(_userDisplayNameKey);
  }
}

class InMemorySessionStore implements SessionStore {
  AppSession? _session;

  @override
  Future<void> clear() async {
    _session = null;
  }

  @override
  Future<AppSession?> read() async => _session;

  @override
  Future<void> write(AppSession session) async {
    _session = session;
  }
}

class MobileApiException implements Exception {
  const MobileApiException(this.message);

  final String message;
}

class AppSession {
  AppSession({
    required this.accessToken,
    required this.expiresAt,
    required this.user,
  });

  factory AppSession.fromJson(Map<String, dynamic> json) {
    return AppSession(
      accessToken: json['access_token'] as String,
      expiresAt: json['expires_at'] as String,
      user: AppUser.fromJson(json['user'] as Map<String, dynamic>),
    );
  }

  final String accessToken;
  final String expiresAt;
  final AppUser user;
}

class AppUser {
  AppUser({
    required this.userId,
    required this.email,
    this.displayName,
  });

  factory AppUser.fromJson(Map<String, dynamic> json) {
    return AppUser(
      userId: json['user_id'] as String,
      email: json['email'] as String,
      displayName: json['display_name'] as String?,
    );
  }

  final String userId;
  final String email;
  final String? displayName;
}

class ParsedFilters {
  ParsedFilters({
    this.location,
    this.minPrice,
    this.maxPrice,
    this.travelMonth,
    this.skillLevel,
  });

  factory ParsedFilters.fromJson(Map<String, dynamic> json) {
    return ParsedFilters(
      location: json['location'] as String?,
      minPrice: (json['min_price'] as num?)?.toDouble(),
      maxPrice: (json['max_price'] as num?)?.toDouble(),
      travelMonth: json['travel_month'] as int?,
      skillLevel: json['skill_level'] as String?,
    );
  }

  final String? location;
  final double? minPrice;
  final double? maxPrice;
  final int? travelMonth;
  final String? skillLevel;
}

class SearchResultItem {
  SearchResultItem({
    required this.resortId,
    required this.resortName,
    required this.selectedSkiAreaName,
    required this.selectedStayBaseName,
    required this.conditionsSummary,
    required this.snowConfidenceLabel,
    required this.availabilityStatus,
    required this.travelMonth,
    this.planningSummary,
    this.recommendationNarrative,
  });

  factory SearchResultItem.fromJson(Map<String, dynamic> json) {
    return SearchResultItem(
      resortId: json['resort_id'] as String,
      resortName: json['resort_name'] as String,
      selectedSkiAreaName: json['selected_ski_area_name'] as String,
      selectedStayBaseName: json['selected_stay_base_name'] as String,
      conditionsSummary: json['conditions_summary'] as String? ??
          'Conditions summary unavailable.',
      snowConfidenceLabel: json['snow_confidence_label'] as String,
      availabilityStatus: json['availability_status'] as String,
      travelMonth: json['travel_month'] as int?,
      planningSummary: json['planning_summary'] as String?,
      recommendationNarrative: json['recommendation_narrative'] as String?,
    );
  }

  final String resortId;
  final String resortName;
  final String selectedSkiAreaName;
  final String selectedStayBaseName;
  final String conditionsSummary;
  final String snowConfidenceLabel;
  final String availabilityStatus;
  final int? travelMonth;
  final String? planningSummary;
  final String? recommendationNarrative;
}

class CurrentTripSummaryData {
  CurrentTripSummaryData({
    required this.tripResortName,
    required this.selectedSkiAreaName,
    required this.selectedStayBaseName,
    required this.currentWeatherSummary,
    required this.comparisonLabel,
    required this.deltaSummary,
    required this.changes,
  });

  factory CurrentTripSummaryData.fromJson(Map<String, dynamic> json) {
    final trip = json['trip'] as Map<String, dynamic>;
    final currentConditions = json['current_conditions'] as Map<String, dynamic>;
    final comparisonBasis = json['comparison_basis'] as Map<String, dynamic>;
    final delta = json['delta'] as Map<String, dynamic>;
    return CurrentTripSummaryData(
      tripResortName: trip['resort_name'] as String,
      selectedSkiAreaName: trip['selected_ski_area_name'] as String,
      selectedStayBaseName: trip['selected_stay_base_name'] as String,
      currentWeatherSummary: currentConditions['weather_summary'] as String,
      comparisonLabel: comparisonBasis['label'] as String,
      deltaSummary: delta['summary'] as String,
      changes: (delta['changes'] as List<dynamic>? ?? const [])
          .map((value) => value as String)
          .toList(),
    );
  }

  final String tripResortName;
  final String selectedSkiAreaName;
  final String selectedStayBaseName;
  final String currentWeatherSummary;
  final String comparisonLabel;
  final String deltaSummary;
  final List<String> changes;
}
