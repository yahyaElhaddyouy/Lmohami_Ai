class ChatSource {
  const ChatSource({required this.number, required this.page});

  final int number;
  final String page;

  factory ChatSource.fromJson(Map<String, dynamic> json) {
    return ChatSource(
      number: _parseInt(json['number']),
      page: (json['page'] ?? '').toString(),
    );
  }

  static int _parseInt(Object? value) {
    if (value is int) {
      return value;
    }
    return int.tryParse(value?.toString() ?? '') ?? 0;
  }
}

class ChatResponse {
  const ChatResponse({required this.answer, required this.sources});

  final String answer;
  final List<ChatSource> sources;

  factory ChatResponse.fromJson(Map<String, dynamic> json) {
    final rawSources = json['sources'];
    final sources = rawSources is List
        ? rawSources
              .whereType<Map<String, dynamic>>()
              .map(ChatSource.fromJson)
              .toList()
        : <ChatSource>[];

    return ChatResponse(
      answer: (json['answer'] ?? '').toString(),
      sources: sources,
    );
  }
}
