class ApiConfig {
  ApiConfig._();

  static const String baseUrl = 'https://astronomy-sustained-elevation.ngrok-free.dev';

  static Uri get chatUri => Uri.parse('$baseUrl/chat');

  static const Duration requestTimeout = Duration(seconds: 300);
}