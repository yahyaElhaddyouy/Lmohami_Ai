enum ApiEnvironment { localEmulator, realPhoneLan, ngrokPublic }

class ApiConfig {
  ApiConfig._();

  static const ApiEnvironment environment = ApiEnvironment.ngrokPublic;

  static const String localEmulatorUrl = 'http://10.0.2.2:8000';
  static const String realPhoneLanUrl = String.fromEnvironment(
    'LMO7AMI_LAN_API_URL',
    defaultValue: 'http://192.168.1.10:8000',
  );
  static const String ngrokPublicUrl =
      'https://astronomy-sustained-elevation.ngrok-free.dev';
  static const String overrideBaseUrl = String.fromEnvironment(
    'LMO7AMI_API_BASE_URL',
    defaultValue: '',
  );
  static const String apiKey = String.fromEnvironment(
    'LMO7AMI_API_KEY',
    defaultValue: '',
  );

  static String get baseUrl {
    final override = overrideBaseUrl.trim();
    if (override.isNotEmpty) {
      return _withoutTrailingSlash(override);
    }

    final configuredUrl = switch (environment) {
      ApiEnvironment.localEmulator => localEmulatorUrl,
      ApiEnvironment.realPhoneLan => realPhoneLanUrl,
      ApiEnvironment.ngrokPublic => ngrokPublicUrl,
    };
    return _withoutTrailingSlash(configuredUrl);
  }

  static String get environmentLabel => switch (environment) {
    ApiEnvironment.localEmulator => 'Local emulator',
    ApiEnvironment.realPhoneLan => 'LAN phone',
    ApiEnvironment.ngrokPublic => 'Ngrok public',
  };

  static Uri get chatUri => Uri.parse('$baseUrl/chat');
  static Uri get healthUri => Uri.parse('$baseUrl/health');

  static Map<String, String> get jsonHeaders {
    return {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      'ngrok-skip-browser-warning': 'true',
      if (apiKey.isNotEmpty) 'X-API-Key': apiKey,
    };
  }

  static const Duration requestTimeout = Duration(seconds: 300);

  static String _withoutTrailingSlash(String value) {
    return value.trim().replaceFirst(RegExp(r'/+$'), '');
  }
}
