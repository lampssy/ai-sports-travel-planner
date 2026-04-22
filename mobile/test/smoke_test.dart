import 'package:flutter_test/flutter_test.dart';
import 'package:snowcast_mobile/main.dart';

void main() {
  testWidgets('renders mobile sign-in screen', (tester) async {
    await tester.pumpWidget(const SnowcastApp());

    expect(find.text('Snowcast Mobile'), findsOneWidget);
    expect(find.text('Sign in with Google'), findsOneWidget);
  });
}
