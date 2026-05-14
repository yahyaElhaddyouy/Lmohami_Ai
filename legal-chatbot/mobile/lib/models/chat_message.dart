import 'chat_response.dart';

enum ChatMessageRole { user, assistant }

class ChatMessage {
  const ChatMessage({
    required this.id,
    required this.role,
    required this.text,
    required this.createdAt,
    this.sources = const [],
    this.isLoading = false,
    this.isError = false,
    this.retryQuestion,
  });

  final String id;
  final ChatMessageRole role;
  final String text;
  final DateTime createdAt;
  final List<ChatSource> sources;
  final bool isLoading;
  final bool isError;
  final String? retryQuestion;

  bool get isUser => role == ChatMessageRole.user;

  ChatMessage copyWith({
    String? id,
    ChatMessageRole? role,
    String? text,
    DateTime? createdAt,
    List<ChatSource>? sources,
    bool? isLoading,
    bool? isError,
    String? retryQuestion,
  }) {
    return ChatMessage(
      id: id ?? this.id,
      role: role ?? this.role,
      text: text ?? this.text,
      createdAt: createdAt ?? this.createdAt,
      sources: sources ?? this.sources,
      isLoading: isLoading ?? this.isLoading,
      isError: isError ?? this.isError,
      retryQuestion: retryQuestion ?? this.retryQuestion,
    );
  }
}
