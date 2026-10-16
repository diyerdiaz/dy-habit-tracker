import 'package:flutter_test/flutter_test.dart';
import 'package:habits/main.dart';

void main() {
  test('La app abre Habits por HTTPS', () {
    final url = Uri.parse(urlInicio);
    expect(url.scheme, 'https');
    expect(url.host, 'habits.proyecto.lol');
  });
}
