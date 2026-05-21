import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import '../config/api_config.dart';
import '../models/chat_response.dart';

class ChatApiException implements Exception {
  const ChatApiException(this.message);

  final String message;

  @override
  String toString() => message;
}

class ChatApiService {
  ChatApiService({http.Client? client}) : _client = client ?? http.Client();

  final http.Client _client;

  Future<ChatResponse> askQuestion(String question) async {
    final requestBody = jsonEncode({'question': question});

    _log('POST ${ApiConfig.chatUri}');
    _log('Base URL: ${ApiConfig.baseUrl}');
    _log('Request body: $requestBody');

    try {
      final response = await _client
          .post(
            ApiConfig.chatUri,
            headers: {
              'Content-Type': 'application/json',
              'Accept': 'application/json',
              'ngrok-skip-browser-warning': 'true',
            },
            body: requestBody,
          )
          .timeout(ApiConfig.requestTimeout);

      final responseBody = utf8.decode(response.bodyBytes);
      _log('Response status: ${response.statusCode}');
      _log('Response body: $responseBody');

      if (response.statusCode >= 500) {
        throw ChatApiException(
          'السيرفر فيه مشكل دابا. الرابط المستعمل: ${ApiConfig.chatUri}',
        );
      }

      if (response.statusCode >= 400) {
        throw ChatApiException(
          'السؤال ما توصلش مزيان للسيرفر. الرابط المستعمل: ${ApiConfig.chatUri}',
        );
      }

      final decoded = jsonDecode(responseBody);
      if (decoded is! Map<String, dynamic>) {
        throw const ChatApiException(
          'الجواب ديال السيرفر ما مفهومش. عاود جرّب.',
        );
      }

      final chatResponse = ChatResponse.fromJson(decoded);
      if (chatResponse.answer.trim().isEmpty) {
        throw const ChatApiException('السيرفر رجّع جواب خاوي. عاود جرّب.');
      }

      return chatResponse;
    } on ChatApiException catch (error, stackTrace) {
      _logException(error, stackTrace);
      rethrow;
    } on SocketException catch (error, stackTrace) {
      _logException(error, stackTrace);
      throw ChatApiException(
        'ما قدرناش نتاصلو بالسيرفر. التطبيق كيستعمل: ${ApiConfig.chatUri}. '
        'فالتليفون الحقيقي خاص الرابط يكون IP ديال الPC فالشبكة، ماشي 10.0.2.2.',
      );
    } on TimeoutException catch (error, stackTrace) {
      _logException(error, stackTrace);
      throw ChatApiException(
        'الاتصال طول بزاف. التطبيق كيستعمل: ${ApiConfig.chatUri}. '
        'تأكد أن التليفون والPC فنفس Wi-Fi وأن Firewall سامح للport 8000.',
      );
    } on FormatException catch (error, stackTrace) {
      _logException(error, stackTrace);
      throw const ChatApiException(
        'الجواب ديال السيرفر ماشي JSON صالح. شوف الbackend وعاود جرّب.',
      );
    } on http.ClientException catch (error, stackTrace) {
      _logException(error, stackTrace);
      throw ChatApiException(
        'وقع مشكل فالاتصال. التطبيق كيستعمل: ${ApiConfig.chatUri}.',
      );
    } catch (error, stackTrace) {
      _logException(error, stackTrace);
      throw const ChatApiException(
        'وقع مشكل غير متوقع فالاتصال. شوف Flutter console logs وعاود جرّب.',
      );
    }
  }

  void dispose() {
    _client.close();
  }

  // Keep these logs visible during device networking setup.
  void _log(String message) {
    debugPrint('[ChatApiService] $message');
  }

  void _logException(Object error, StackTrace stackTrace) {
    debugPrint('[ChatApiService] Exception: $error');
    debugPrint('[ChatApiService] Stack trace: $stackTrace');
  }
}
