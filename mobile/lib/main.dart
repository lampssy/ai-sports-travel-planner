import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import 'api_errors.dart';
import 'public_copy.dart';

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
  }) : _api = api,
       _authController = authController;

  final MobileApiClient? _api;
  final AuthController? _authController;

  @override
  Widget build(BuildContext context) {
    final api = _api ?? MobileApiClient(baseUrl: _apiBaseUrl);
    final authController =
        _authController ??
        AuthController(
          api: api,
          sessionStore: SharedPreferencesSessionStore(SharedPreferencesAsync()),
        );

    return MaterialApp(
      title: PublicCopy.appName,
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
          return MobileShell(api: api, authController: authController);
        },
      ),
    );
  }
}

class AuthController extends ChangeNotifier {
  AuthController({required this.api, required this.sessionStore});

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
        throw PublicApiException.response(
          '{"error":{"code":"sign_in_failed"}}',
        );
      }

      final newSession = await api.exchangeGoogleIdentityToken(identityToken);
      await sessionStore.write(newSession);
      session = newSession;
    } on GoogleSignInException {
      errorMessage = 'Sign-in could not be completed. Try again.';
    } on PublicApiException catch (error) {
      errorMessage = apiErrorMessage(ApiOperation.signIn, error);
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

  Future<bool> handleProtectedFailure(PublicApiException error) async {
    if (error.code != PublicApiErrorCode.sessionExpired) {
      return false;
    }
    if (session != null) {
      await sessionStore.clear();
      session = null;
      errorMessage = PublicCopy.sessionEnded;
      notifyListeners();
    }
    return true;
  }

  Future<void> _ensureGoogleInitialized() async {
    if (_googleInitialized) {
      return;
    }
    await GoogleSignIn.instance.initialize(
      serverClientId: _googleServerClientId.isEmpty
          ? null
          : _googleServerClientId,
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
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 420),
              child: Card(
                child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: Semantics(
                    container: true,
                    explicitChildNodes: true,
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Semantics(
                          container: true,
                          header: true,
                          child: Focus(
                            autofocus: true,
                            child: Text(
                              PublicCopy.signInHeading,
                              style: Theme.of(context).textTheme.headlineMedium,
                            ),
                          ),
                        ),
                        const SizedBox(height: 12),
                        const Text(
                          'Sign in with Google to save one current trip and receive trip updates.',
                        ),
                        if (authController.errorMessage != null) ...[
                          const SizedBox(height: 16),
                          Semantics(
                            container: true,
                            liveRegion: true,
                            child: Text(
                              authController.errorMessage!,
                              style: TextStyle(
                                color: Theme.of(context).colorScheme.error,
                              ),
                            ),
                          ),
                        ],
                        const SizedBox(height: 24),
                        FilledButton.icon(
                          onPressed: authController.isBusy
                              ? null
                              : authController.signInWithGoogle,
                          icon: const Icon(Icons.login),
                          label: const Text('Sign in with Google'),
                        ),
                      ],
                    ),
                  ),
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
      SearchScreen(
        api: widget.api,
        session: session,
        authController: widget.authController,
      ),
      CurrentTripScreen(
        api: widget.api,
        session: session,
        authController: widget.authController,
      ),
    ];

    return Scaffold(
      appBar: AppBar(
        title: Text(_selectedIndex == 0 ? 'Plan trip' : PublicCopy.currentTrip),
        actions: [
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
          NavigationDestination(icon: Icon(Icons.search), label: 'Search'),
          NavigationDestination(
            icon: Icon(Icons.downhill_skiing),
            label: PublicCopy.currentTrip,
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
    required this.authController,
  });

  final MobileApiClient api;
  final AppSession session;
  final AuthController authController;

  @override
  State<SearchScreen> createState() => _SearchScreenState();
}

class _SearchScreenState extends State<SearchScreen> {
  final _briefController = TextEditingController();
  final _locationController = TextEditingController(text: 'France');
  final _maxPriceController = TextEditingController(text: '320');

  String _skillLevel = 'intermediate';
  int _stars = 1;
  int? _travelMonth = 3;
  String? _tripStartDate;
  String? _tripEndDate;
  bool _isBusy = false;
  String? _errorMessage;
  List<RecommendationGroupItem> _results = const [];

  @override
  void dispose() {
    _briefController.dispose();
    _locationController.dispose();
    _maxPriceController.dispose();
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
      final parsed = await widget.api.parseTripBrief(
        _briefController.text.trim(),
      );
      _locationController.text = parsed.location ?? _locationController.text;
      if (parsed.maxPrice != null) {
        _maxPriceController.text = parsed.maxPrice!.toStringAsFixed(0);
      }
      if (parsed.tripStartDate != null && parsed.tripEndDate != null) {
        _tripStartDate = parsed.tripStartDate;
        _tripEndDate = parsed.tripEndDate;
        _travelMonth = null;
      } else if (parsed.travelMonth != null) {
        _travelMonth = parsed.travelMonth;
        _tripStartDate = null;
        _tripEndDate = null;
      }
      if (parsed.skillLevel != null) {
        _skillLevel = parsed.skillLevel!;
      }
    } on PublicApiException catch (error) {
      _errorMessage = apiErrorMessage(ApiOperation.parseTripBrief, error);
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
      final tripStartDate = _tripStartDate;
      final tripEndDate = _tripEndDate;
      final hasTripStartDate = tripStartDate != null;
      final hasTripEndDate = tripEndDate != null;

      if (hasTripStartDate != hasTripEndDate) {
        setState(() {
          _errorMessage =
              'Provide both trip start and end dates, or leave both empty.';
        });
        return;
      }

      if (tripStartDate != null && tripEndDate != null) {
        final startDate = DateTime.parse(tripStartDate);
        final endDate = DateTime.parse(tripEndDate);
        if (endDate.isBefore(startDate)) {
          setState(() {
            _errorMessage = 'Trip end date must be on or after start date.';
          });
          return;
        }
      }

      final response = await widget.api.search(
        location: _locationController.text.trim(),
        maxPrice: double.parse(_maxPriceController.text),
        stars: _stars,
        skillLevel: _skillLevel,
        travelMonth: hasTripStartDate && hasTripEndDate ? null : _travelMonth,
        tripStartDate: hasTripStartDate ? tripStartDate : null,
        tripEndDate: hasTripEndDate ? tripEndDate : null,
        brief: _briefController.text.trim(),
      );
      setState(() {
        _results = response.results;
      });
    } on FormatException {
      setState(() {
        _errorMessage = 'Prices must be valid numbers.';
      });
    } on PublicApiException catch (error) {
      setState(() {
        _errorMessage = apiErrorMessage(ApiOperation.search, error);
      });
    } finally {
      setState(() {
        _isBusy = false;
      });
    }
  }

  Future<void> _pickTripDate({required bool start}) async {
    final current = DateTime.tryParse(
      start ? _tripStartDate ?? '' : _tripEndDate ?? '',
    );
    final selected = await showDatePicker(
      context: context,
      initialDate: current ?? DateTime.now(),
      firstDate: DateTime.now().subtract(const Duration(days: 365)),
      lastDate: DateTime.now().add(const Duration(days: 365 * 5)),
      helpText: start ? 'Choose trip start date' : 'Choose trip end date',
    );
    if (selected == null || !mounted) {
      return;
    }
    final value = selected.toIso8601String().substring(0, 10);
    setState(() {
      if (start) {
        _tripStartDate = value;
      } else {
        _tripEndDate = value;
      }
      _travelMonth = null;
    });
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
                  '${PublicCopy.mustHaves} and ${PublicCopy.preferences}',
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
                TextField(
                  controller: _maxPriceController,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(
                    labelText: 'Maximum nightly lodging estimate',
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 12),
                DropdownButtonFormField<int>(
                  initialValue: _stars,
                  decoration: const InputDecoration(
                    labelText: 'Stay comfort',
                    border: OutlineInputBorder(),
                  ),
                  items: PublicCopy.qualityLabels.entries
                      .map(
                        (entry) => DropdownMenuItem(
                          value: entry.key,
                          child: Text(entry.value),
                        ),
                      )
                      .toList(),
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
                DropdownButtonFormField<int?>(
                  initialValue: _travelMonth,
                  decoration: const InputDecoration(
                    labelText: 'Travel month (optional)',
                    border: OutlineInputBorder(),
                  ),
                  items: [
                    const DropdownMenuItem<int?>(
                      value: null,
                      child: Text('Choose exact dates'),
                    ),
                    for (var month = 1; month <= 12; month += 1)
                      DropdownMenuItem<int?>(
                        value: month,
                        child: Text(PublicCopy.monthNames[month - 1]),
                      ),
                  ],
                  onChanged: (value) {
                    setState(() {
                      _travelMonth = value;
                      if (value != null) {
                        _tripStartDate = null;
                        _tripEndDate = null;
                      }
                    });
                  },
                ),
                const SizedBox(height: 12),
                Wrap(
                  spacing: 12,
                  runSpacing: 12,
                  children: [
                    OutlinedButton.icon(
                      onPressed: () => _pickTripDate(start: true),
                      icon: const Icon(Icons.calendar_today),
                      label: Text(
                        _tripStartDate == null
                            ? 'Choose start date'
                            : 'Starts ${formatPublicDate(_tripStartDate!)}',
                      ),
                    ),
                    OutlinedButton.icon(
                      onPressed: () => _pickTripDate(start: false),
                      icon: const Icon(Icons.event),
                      label: Text(
                        _tripEndDate == null
                            ? 'Choose end date'
                            : 'Ends ${formatPublicDate(_tripEndDate!)}',
                      ),
                    ),
                  ],
                ),
                if (_errorMessage != null) ...[
                  const SizedBox(height: 12),
                  Semantics(
                    liveRegion: true,
                    child: Text(
                      _errorMessage!,
                      style: TextStyle(
                        color: Theme.of(context).colorScheme.error,
                      ),
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
            child: Text('Search to find trip options.'),
          ),
        if (_results.isNotEmpty) ...[
          Text(
            PublicCopy.tripOptions,
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 12),
        ],
        for (final result in _results)
          RecommendationGroupCard(
            result: result,
            session: widget.session,
            api: widget.api,
            authController: widget.authController,
            travelMonth: _travelMonth,
            tripStartDate: _tripStartDate ?? '',
            tripEndDate: _tripEndDate ?? '',
          ),
      ],
    );
  }
}

class RecommendationGroupCard extends StatefulWidget {
  const RecommendationGroupCard({
    super.key,
    required this.result,
    required this.session,
    required this.api,
    required this.authController,
    required this.travelMonth,
    required this.tripStartDate,
    required this.tripEndDate,
  });

  final RecommendationGroupItem result;
  final AppSession session;
  final MobileApiClient api;
  final AuthController authController;
  final int? travelMonth;
  final String tripStartDate;
  final String tripEndDate;

  @override
  State<RecommendationGroupCard> createState() =>
      _RecommendationGroupCardState();
}

class _RecommendationGroupCardState extends State<RecommendationGroupCard> {
  bool _saving = false;
  String? _message;

  Future<void> _saveCurrentTrip() async {
    setState(() {
      _saving = true;
      _message = null;
    });

    try {
      final hasCompleteTripWindow =
          widget.tripStartDate.isNotEmpty && widget.tripEndDate.isNotEmpty;
      await widget.api.saveCurrentTrip(
        token: widget.session.accessToken,
        result: widget.result,
        travelMonth: widget.travelMonth,
        tripStartDate: hasCompleteTripWindow ? widget.tripStartDate : null,
        tripEndDate: hasCompleteTripWindow ? widget.tripEndDate : null,
      );
      setState(() {
        _message = 'Saved as current trip.';
      });
    } on PublicApiException catch (error) {
      if (await widget.authController.handleProtectedFailure(error) ||
          !mounted) {
        return;
      }
      setState(() {
        _message = apiErrorMessage(ApiOperation.currentTripSave, error);
      });
    } finally {
      if (mounted) {
        setState(() {
          _saving = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final result = widget.result;
    final tripOption = result.topConfiguration;
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              result.skiRegionName,
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 8),
            Text(
              '${PublicCopy.tripOption}: stay in ${tripOption.stayBaseName} '
              'and ski ${tripOption.focusSkiAreaName}.',
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                Chip(label: Text(tripOption.stayDestinationName)),
                Chip(label: Text(tripOption.focusSkiAreaName)),
                Chip(label: Text(tripOption.stayBaseName)),
                Chip(label: Text(tripOption.selectedPass.name)),
                Chip(
                  label: Text(
                    tripOption.selectedPass.accessiblePisteKm == null
                        ? 'Pass terrain details unavailable'
                        : '${tripOption.selectedPass.accessiblePisteKm} km of pass terrain',
                  ),
                ),
              ],
            ),
            if (result.alternativeConfigurations.isNotEmpty) ...[
              const SizedBox(height: 8),
              Text(
                '${result.alternativeConfigurations.length} alternative trip '
                'option${result.alternativeConfigurations.length == 1 ? '' : 's'}',
              ),
            ],
            const SizedBox(height: 12),
            FilledButton(
              onPressed: _saving ? null : _saveCurrentTrip,
              child: Text(_saving ? 'Saving...' : 'Save as current trip'),
            ),
            if (_message != null) ...[
              const SizedBox(height: 8),
              Semantics(liveRegion: true, child: Text(_message!)),
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
    required this.authController,
  });

  final MobileApiClient api;
  final AppSession session;
  final AuthController authController;

  @override
  State<CurrentTripScreen> createState() => _CurrentTripScreenState();
}

class _CurrentTripScreenState extends State<CurrentTripScreen> {
  bool _summaryLoading = true;
  bool _eventsLoading = true;
  bool _markingChecked = false;
  String? _summaryError;
  String? _eventsError;
  String? _markCheckedError;
  CurrentTripSummaryData? _summary;
  List<CurrentTripEvent> _events = const [];

  @override
  void initState() {
    super.initState();
    unawaited(_loadSummary());
    unawaited(_loadEvents());
  }

  Future<void> _loadSummary() async {
    setState(() {
      _summaryLoading = true;
      _summaryError = null;
    });

    try {
      final summary = await widget.api.getCurrentTripSummary(
        token: widget.session.accessToken,
      );
      if (!mounted) {
        return;
      }
      setState(() {
        _summary = summary;
      });
    } on PublicApiException catch (error) {
      if (await widget.authController.handleProtectedFailure(error) ||
          !mounted) {
        return;
      }
      setState(() {
        _summaryError = apiErrorMessage(ApiOperation.currentTripSummary, error);
      });
    } finally {
      if (mounted) {
        setState(() {
          _summaryLoading = false;
        });
      }
    }
  }

  Future<void> _loadEvents() async {
    setState(() {
      _eventsLoading = true;
      _eventsError = null;
    });

    try {
      final events = await widget.api.getCurrentTripEvents(
        token: widget.session.accessToken,
      );
      if (!mounted) {
        return;
      }
      setState(() {
        _events = events;
      });
    } on PublicApiException catch (error) {
      if (await widget.authController.handleProtectedFailure(error) ||
          !mounted) {
        return;
      }
      setState(() {
        if (error.code == PublicApiErrorCode.currentTripNotFound) {
          _events = const [];
          _eventsError = null;
        } else {
          _eventsError = apiErrorMessage(ApiOperation.currentTripEvents, error);
        }
      });
    } finally {
      if (mounted) {
        setState(() {
          _eventsLoading = false;
        });
      }
    }
  }

  Future<void> _markChecked() async {
    setState(() {
      _markingChecked = true;
      _markCheckedError = null;
    });

    try {
      await widget.api.markCurrentTripChecked(
        token: widget.session.accessToken,
      );
      if (!mounted) {
        return;
      }
      await Future.wait([_loadSummary(), _loadEvents()]);
    } on PublicApiException catch (error) {
      if (await widget.authController.handleProtectedFailure(error) ||
          !mounted) {
        return;
      }
      setState(() {
        if (error.code == PublicApiErrorCode.currentTripNotFound) {
          _summary = null;
          _events = const [];
          _markCheckedError = null;
        } else {
          _markCheckedError = apiErrorMessage(
            ApiOperation.currentTripMarkChecked,
            error,
          );
        }
      });
    } finally {
      if (mounted) {
        setState(() {
          _markingChecked = false;
        });
      }
    }
  }

  Future<void> _refreshAll() async {
    await Future.wait([_loadSummary(), _loadEvents()]);
  }

  Widget _buildSummary(BuildContext context) {
    if (_summaryLoading && _summary == null) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_summaryError != null && _summary == null) {
      return InlineRecovery(
        message: _summaryError!,
        semanticsLabel: 'Try loading current trip again',
        onRetry: _loadSummary,
      );
    }
    if (_summary == null) {
      return const Padding(
        padding: EdgeInsets.symmetric(vertical: 48),
        child: Center(child: Text('No current trip is saved.')),
      );
    }

    final summary = _summary!;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              summary.skiRegionName,
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 8),
            Text(summary.focusSkiAreaName),
            Text(summary.stayBaseName),
            if (summary.tripStartDate != null && summary.tripEndDate != null)
              Text(
                formatPublicDateRange(
                  summary.tripStartDate!,
                  summary.tripEndDate!,
                ),
              ),
            const SizedBox(height: 12),
            Text(summary.currentWeatherSummary),
            const SizedBox(height: 12),
            Text(summary.eligibilityReason),
            Text(summary.deltaSummary),
            if (summary.changes.isNotEmpty) ...[
              const SizedBox(height: 12),
              Text(
                'What changed',
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: 8),
              for (final change in summary.changes)
                Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Text('• $change'),
                ),
            ],
            const SizedBox(height: 12),
            FilledButton.icon(
              onPressed: _markingChecked ? null : _markChecked,
              icon: const Icon(Icons.check),
              label: Text(_markingChecked ? 'Updating...' : 'Mark checked'),
            ),
            if (_markCheckedError != null) ...[
              const SizedBox(height: 12),
              InlineRecovery(
                message: _markCheckedError!,
                semanticsLabel: 'Try marking current trip checked again',
                onRetry: _markChecked,
              ),
            ],
            if (_summaryError != null) ...[
              const SizedBox(height: 12),
              InlineRecovery(
                message: _summaryError!,
                semanticsLabel: 'Try loading current trip again',
                onRetry: _loadSummary,
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildEvents(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              PublicCopy.tripUpdates,
              style: Theme.of(context).textTheme.titleMedium,
            ),
            if (_eventsLoading && _events.isEmpty) ...[
              const SizedBox(height: 12),
              const LinearProgressIndicator(),
            ],
            if (!_eventsLoading && _events.isEmpty && _eventsError == null) ...[
              const SizedBox(height: 8),
              const Text('No trip updates yet.'),
            ],
            if (_events.isNotEmpty) ...[
              const SizedBox(height: 8),
              for (final event in _events) ...[
                Text(event.summary),
                const SizedBox(height: 2),
                Text(
                  formatPublicDate(event.recordedAt),
                  style: Theme.of(context).textTheme.bodySmall,
                ),
                const SizedBox(height: 12),
              ],
            ],
            if (_eventsError != null) ...[
              InlineRecovery(
                message: _eventsError!,
                semanticsLabel: 'Try loading trip updates again',
                onRetry: _loadEvents,
              ),
            ],
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final showEvents =
        _summary != null || _summaryLoading || _summaryError != null;
    return RefreshIndicator(
      onRefresh: _refreshAll,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(16),
        children: [
          _buildSummary(context),
          if (showEvents) ...[
            const SizedBox(height: 12),
            _buildEvents(context),
          ],
        ],
      ),
    );
  }
}

class InlineRecovery extends StatelessWidget {
  const InlineRecovery({
    super.key,
    required this.message,
    required this.semanticsLabel,
    required this.onRetry,
  });

  final String message;
  final String semanticsLabel;
  final Future<void> Function() onRetry;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      liveRegion: true,
      container: true,
      explicitChildNodes: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Semantics(
            container: true,
            child: Text(
              message,
              style: TextStyle(color: Theme.of(context).colorScheme.error),
            ),
          ),
          const SizedBox(height: 8),
          Semantics(
            button: true,
            label: semanticsLabel,
            excludeSemantics: true,
            child: OutlinedButton.icon(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh),
              label: const Text('Try again'),
            ),
          ),
        ],
      ),
    );
  }
}

class MobileApiClient {
  MobileApiClient({required this.baseUrl, http.Client? client})
    : _client = client ?? http.Client();

  final String baseUrl;
  final http.Client _client;

  Future<AppSession> exchangeGoogleIdentityToken(String identityToken) async {
    final payload = await _requestJson(
      () => _client.post(
        Uri.parse('$baseUrl/auth/google/sign-in'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'identity_token': identityToken}),
      ),
    );
    return _decodeModel(() => AppSession.fromJson(payload));
  }

  Future<ParsedFilters> parseTripBrief(String query) async {
    final payload = await _requestJson(
      () => _client.post(
        Uri.parse('$baseUrl/parse-query'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'query': query}),
      ),
    );
    return _decodeModel(
      () => ParsedFilters.fromJson(
        payload['filters'] as Map<String, dynamic>? ?? const {},
      ),
    );
  }

  Future<SearchResponseItem> search({
    required String location,
    required double maxPrice,
    required int stars,
    required String skillLevel,
    int? travelMonth,
    String? tripStartDate,
    String? tripEndDate,
    String? brief,
  }) async {
    final hasTripWindow =
        tripStartDate != null &&
        tripStartDate.isNotEmpty &&
        tripEndDate != null &&
        tripEndDate.isNotEmpty;
    final travelWindow = hasTripWindow
        ? {'start_date': tripStartDate, 'end_date': tripEndDate}
        : travelMonth != null
        ? {'month': travelMonth}
        : null;
    final payload = await _requestJson(
      () => _client.post(
        Uri.parse('$baseUrl/search'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'intent': {
            'constraints': {
              'location': {'country': location},
              'travel_window': ?travelWindow,
              'lodging_budget': {
                'mode': 'lodging_nightly',
                'maximum': maxPrice,
                'currency': 'EUR',
                'budget_flex': 0.10,
              },
              'minimum_stay_quality': {'minimum_score': stars / 3 * 10},
            },
            'party': {
              'skill_levels': [skillLevel],
            },
            'travel_context': <String, dynamic>{},
            'objectives': [
              {'factor_id': 'pass_terrain_value', 'importance': 'normal'},
            ],
            'group_priorities': <Map<String, dynamic>>[],
            'factor_preferences': <Map<String, dynamic>>[],
            'assumptions': <String>[],
          },
          'brief': brief == null || brief.isEmpty ? null : brief,
          'generate_refinements': false,
          'already_answered_question_ids': <String>[],
        }),
      ),
    );
    return _decodeModel(() => SearchResponseItem.fromJson(payload));
  }

  Future<void> saveCurrentTrip({
    required String token,
    required RecommendationGroupItem result,
    int? travelMonth,
    String? tripStartDate,
    String? tripEndDate,
  }) async {
    final configuration = result.topConfiguration;
    await _requestJson(
      () => _client.put(
        Uri.parse('$baseUrl/current-trip'),
        headers: _authorizedHeaders(token),
        body: jsonEncode({
          'ski_region_id': result.skiRegionId,
          'ski_region_name': result.skiRegionName,
          'stay_destination_id': configuration.stayDestinationId,
          'stay_destination_name': configuration.stayDestinationName,
          'stay_base_id': configuration.stayBaseId,
          'stay_base_name': configuration.stayBaseName,
          'focus_ski_area_id': configuration.focusSkiAreaId,
          'focus_ski_area_name': configuration.focusSkiAreaName,
          'lift_pass_product_id': configuration.selectedPass.liftPassProductId,
          'lift_pass_product_name': configuration.selectedPass.name,
          'travel_month': travelMonth,
          'trip_start_date': tripStartDate,
          'trip_end_date': tripEndDate,
          'booking_status': 'not_booked_yet',
        }),
      ),
    );
  }

  Future<CurrentTripSummaryData?> getCurrentTripSummary({
    required String token,
  }) async {
    final response = await _request(
      () => _client.get(
        Uri.parse('$baseUrl/current-trip/summary'),
        headers: _authorizedHeaders(token, includeContentType: false),
      ),
    );
    if (response.statusCode >= 400) {
      final failure = PublicApiException.response(response.body);
      if (failure.code == PublicApiErrorCode.currentTripNotFound) {
        return null;
      }
      throw failure;
    }
    final payload = _decodeSuccessJson(response);
    return _decodeModel(() => CurrentTripSummaryData.fromJson(payload));
  }

  Future<void> markCurrentTripChecked({required String token}) async {
    await _requestJson(
      () => _client.post(
        Uri.parse('$baseUrl/current-trip/mark-checked'),
        headers: _authorizedHeaders(token, includeContentType: false),
      ),
    );
  }

  Future<List<CurrentTripEvent>> getCurrentTripEvents({
    required String token,
  }) async {
    final payload = await _requestJson(
      () => _client.get(
        Uri.parse('$baseUrl/current-trip/events'),
        headers: _authorizedHeaders(token, includeContentType: false),
      ),
    );
    return _decodeModel(() {
      final events = payload['events'] as List<dynamic>? ?? const [];
      return events
          .map(
            (event) => CurrentTripEvent.fromJson(event as Map<String, dynamic>),
          )
          .toList();
    });
  }

  Future<http.Response> _request(Future<http.Response> Function() send) async {
    try {
      return await send();
    } on PublicApiException {
      rethrow;
    } catch (error) {
      throw PublicApiException.transport(error);
    }
  }

  Future<Map<String, dynamic>> _requestJson(
    Future<http.Response> Function() send,
  ) async {
    final response = await _request(send);
    if (response.statusCode >= 400) {
      throw PublicApiException.response(response.body);
    }
    return _decodeSuccessJson(response);
  }

  Map<String, dynamic> _decodeSuccessJson(http.Response response) {
    if (response.body.isEmpty) {
      return const {};
    }
    try {
      final payload = jsonDecode(response.body);
      if (payload is! Map<String, dynamic>) {
        throw const FormatException('Expected a JSON object.');
      }
      return payload;
    } catch (error) {
      throw PublicApiException.decode(error);
    }
  }

  T _decodeModel<T>(T Function() decode) {
    try {
      return decode();
    } on PublicApiException {
      rethrow;
    } catch (error) {
      throw PublicApiException.decode(error);
    }
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
  AppUser({required this.userId, required this.email, this.displayName});

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
    this.tripStartDate,
    this.tripEndDate,
    this.skillLevel,
  });

  factory ParsedFilters.fromJson(Map<String, dynamic> json) {
    return ParsedFilters(
      location: json['location'] as String?,
      minPrice: (json['min_price'] as num?)?.toDouble(),
      maxPrice: (json['max_price'] as num?)?.toDouble(),
      travelMonth: json['travel_month'] as int?,
      tripStartDate: json['trip_start_date'] as String?,
      tripEndDate: json['trip_end_date'] as String?,
      skillLevel: json['skill_level'] as String?,
    );
  }

  final String? location;
  final double? minPrice;
  final double? maxPrice;
  final int? travelMonth;
  final String? tripStartDate;
  final String? tripEndDate;
  final String? skillLevel;
}

class SearchResponseItem {
  SearchResponseItem({
    required this.searchModelVersion,
    required this.rankingPolicyVersion,
    required this.rankingStatus,
    required this.results,
  });

  factory SearchResponseItem.fromJson(Map<String, dynamic> json) {
    return SearchResponseItem(
      searchModelVersion: json['search_model_version'] as String,
      rankingPolicyVersion: json['ranking_policy_version'] as String,
      rankingStatus: json['ranking_status'] as String,
      results: (json['results'] as List<dynamic>? ?? const [])
          .map(
            (item) =>
                RecommendationGroupItem.fromJson(item as Map<String, dynamic>),
          )
          .toList(),
    );
  }

  final String searchModelVersion;
  final String rankingPolicyVersion;
  final String rankingStatus;
  final List<RecommendationGroupItem> results;
}

class RecommendationGroupItem {
  RecommendationGroupItem({
    required this.skiRegionId,
    required this.skiRegionName,
    required this.topConfiguration,
    required this.alternativeConfigurations,
  });

  factory RecommendationGroupItem.fromJson(Map<String, dynamic> json) {
    return RecommendationGroupItem(
      skiRegionId: json['ski_region_id'] as String,
      skiRegionName: json['ski_region_name'] as String,
      topConfiguration: TripConfigurationItem.fromJson(
        json['top_configuration'] as Map<String, dynamic>,
      ),
      alternativeConfigurations:
          (json['alternative_configurations'] as List<dynamic>? ?? const [])
              .map(
                (item) => TripConfigurationItem.fromJson(
                  item as Map<String, dynamic>,
                ),
              )
              .toList(),
    );
  }

  final String skiRegionId;
  final String skiRegionName;
  final TripConfigurationItem topConfiguration;
  final List<TripConfigurationItem> alternativeConfigurations;
}

class TripConfigurationItem {
  TripConfigurationItem({
    required this.configurationId,
    required this.stayDestinationId,
    required this.stayDestinationName,
    required this.stayBaseId,
    required this.stayBaseName,
    required this.focusSkiAreaId,
    required this.focusSkiAreaName,
    required this.liftDistance,
    required this.selectedPass,
    required this.fitScore,
  });

  factory TripConfigurationItem.fromJson(Map<String, dynamic> json) {
    final access = json['access'] as Map<String, dynamic>;
    return TripConfigurationItem(
      configurationId: json['candidate_id'] as String,
      stayDestinationId: json['stay_destination_id'] as String,
      stayDestinationName: json['stay_destination_name'] as String,
      stayBaseId: json['stay_base_id'] as String,
      stayBaseName: json['stay_base_name'] as String,
      focusSkiAreaId: json['ski_area_id'] as String,
      focusSkiAreaName: json['ski_area_name'] as String,
      liftDistance: access['lift_distance'] as String,
      selectedPass: PassOptionItem.fromJson(
        json['selected_pass'] as Map<String, dynamic>,
      ),
      fitScore: (json['fit_score'] as num?)?.toDouble(),
    );
  }

  final String configurationId;
  final String stayDestinationId;
  final String stayDestinationName;
  final String stayBaseId;
  final String stayBaseName;
  final String focusSkiAreaId;
  final String focusSkiAreaName;
  final String liftDistance;
  final PassOptionItem selectedPass;
  final double? fitScore;
}

class PassOptionItem {
  PassOptionItem({
    required this.liftPassProductId,
    required this.name,
    required this.accessiblePisteKm,
  });

  factory PassOptionItem.fromJson(Map<String, dynamic> json) {
    return PassOptionItem(
      liftPassProductId: json['lift_pass_product_id'] as String,
      name: json['name'] as String,
      accessiblePisteKm: (json['accessible_piste_km'] as num?)?.toDouble(),
    );
  }

  final String liftPassProductId;
  final String name;
  final double? accessiblePisteKm;
}

class CurrentTripSummaryData {
  CurrentTripSummaryData({
    required this.skiRegionName,
    required this.focusSkiAreaName,
    required this.stayBaseName,
    required this.tripStartDate,
    required this.tripEndDate,
    required this.currentWeatherSummary,
    required this.comparisonLabel,
    required this.tripWindowLabel,
    required this.eligibilityReason,
    required this.deltaSummary,
    required this.changes,
  });

  factory CurrentTripSummaryData.fromJson(Map<String, dynamic> json) {
    final trip = json['trip'] as Map<String, dynamic>;
    final currentConditions =
        json['current_conditions'] as Map<String, dynamic>;
    final comparisonBasis = json['comparison_basis'] as Map<String, dynamic>;
    final delta = json['delta'] as Map<String, dynamic>;
    return CurrentTripSummaryData(
      skiRegionName: trip['ski_region_name'] as String,
      focusSkiAreaName: trip['focus_ski_area_name'] as String,
      stayBaseName: trip['stay_base_name'] as String,
      tripStartDate: trip['trip_start_date'] as String?,
      tripEndDate: trip['trip_end_date'] as String?,
      currentWeatherSummary: currentConditions['weather_summary'] as String,
      comparisonLabel: comparisonBasis['label'] as String,
      tripWindowLabel:
          (json['companion_status']
                  as Map<String, dynamic>)['trip_window_label']
              as String,
      eligibilityReason:
          (json['companion_status']
                  as Map<String, dynamic>)['eligibility_reason']
              as String,
      deltaSummary: delta['summary'] as String,
      changes: (delta['changes'] as List<dynamic>? ?? const [])
          .map((value) => value as String)
          .toList(),
    );
  }

  final String skiRegionName;
  final String focusSkiAreaName;
  final String stayBaseName;
  final String? tripStartDate;
  final String? tripEndDate;
  final String currentWeatherSummary;
  final String comparisonLabel;
  final String tripWindowLabel;
  final String eligibilityReason;
  final String deltaSummary;
  final List<String> changes;
}

class CurrentTripEvent {
  CurrentTripEvent({
    required this.summary,
    required this.recordedAt,
    required this.actionable,
  });

  factory CurrentTripEvent.fromJson(Map<String, dynamic> json) {
    return CurrentTripEvent(
      summary: json['summary'] as String,
      recordedAt: json['recorded_at'] as String,
      actionable: json['actionable'] as bool? ?? false,
    );
  }

  final String summary;
  final String recordedAt;
  final bool actionable;
}
