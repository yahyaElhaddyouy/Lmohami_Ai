import 'package:flutter_test/flutter_test.dart';
import 'package:lmo7ami_ai/main.dart';

void main() {
  testWidgets('shows splash screen', (tester) async {
    await tester.pumpWidget(const Lmo7amiApp());

    expect(find.text('Lmo7ami AI'), findsOneWidget);
    expect(find.text('مساعد قانون الشغل المغربي'), findsOneWidget);
  });
}
