class ApiConfig {
  ApiConfig._();

  static const String localHostBaseUrl = 'http://127.0.0.1:8000';
  static const String androidEmulatorBaseUrl = 'http://10.0.2.2:8000';

  // For a real phone on the same Wi-Fi, change this value to your computer IP.
  // Example: http://192.168.1.42:8000
  static const String realPhoneBaseUrl = 'http://192.168.1.16:8000';

  // USB debugging is using:
  // adb reverse tcp:8000 tcp:8000
  // With that tunnel active, the phone's 127.0.0.1:8000 forwards to the PC.
  static const String baseUrl = localHostBaseUrl;

  static Uri get chatUri => Uri.parse('$baseUrl/chat');

  // Local Ollama responses can be slow, especially on the first request.
  // Keep this aligned with the backend generation timeout.
  static const Duration requestTimeout = Duration(seconds: 330);
}
