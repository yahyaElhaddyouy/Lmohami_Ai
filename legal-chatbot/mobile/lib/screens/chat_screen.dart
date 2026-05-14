import 'package:flutter/material.dart';

import '../models/chat_message.dart';
import '../services/chat_api_service.dart';
import '../theme/app_theme.dart';
import '../widgets/chat_input_bar.dart';
import '../widgets/message_bubble.dart';

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final ChatApiService _apiService = ChatApiService();
  final ScrollController _scrollController = ScrollController();
  final List<ChatMessage> _messages = [
    ChatMessage(
      id: 'welcome',
      role: ChatMessageRole.assistant,
      text:
          'سلام، أنا مساعدك فمدونة الشغل المغربية. سَوّلني على الطرد، العطلة، العقد، التعويضات أو حقوق الأجير.',
      createdAt: DateTime.now(),
    ),
  ];

  bool _isSending = false;

  bool get _hasUserMessages => _messages.any((message) => message.isUser);

  @override
  void dispose() {
    _apiService.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  Future<void> _sendMessage(
    String question, {
    bool addUserMessage = true,
  }) async {
    if (question.trim().isEmpty || _isSending) {
      return;
    }

    final now = DateTime.now();
    final loadingId = 'loading-${now.microsecondsSinceEpoch}';

    setState(() {
      _isSending = true;
      if (addUserMessage) {
        _messages.add(
          ChatMessage(
            id: 'user-${now.microsecondsSinceEpoch}',
            role: ChatMessageRole.user,
            text: question,
            createdAt: now,
          ),
        );
      }
      _messages.add(
        ChatMessage(
          id: loadingId,
          role: ChatMessageRole.assistant,
          text: '',
          createdAt: DateTime.now(),
          isLoading: true,
        ),
      );
    });
    _scrollToBottom();

    try {
      final response = await _apiService.askQuestion(question);
      _replaceMessage(
        loadingId,
        ChatMessage(
          id: 'assistant-${DateTime.now().microsecondsSinceEpoch}',
          role: ChatMessageRole.assistant,
          text: response.answer,
          sources: response.sources,
          createdAt: DateTime.now(),
        ),
      );
    } on ChatApiException catch (error) {
      _replaceMessage(
        loadingId,
        ChatMessage(
          id: 'error-${DateTime.now().microsecondsSinceEpoch}',
          role: ChatMessageRole.assistant,
          text: error.message,
          createdAt: DateTime.now(),
          isError: true,
          retryQuestion: question,
        ),
      );
    } catch (_) {
      _replaceMessage(
        loadingId,
        ChatMessage(
          id: 'error-${DateTime.now().microsecondsSinceEpoch}',
          role: ChatMessageRole.assistant,
          text: 'وقع مشكل غير متوقع. عاود جرّب من فضلك.',
          createdAt: DateTime.now(),
          isError: true,
          retryQuestion: question,
        ),
      );
    } finally {
      if (mounted) {
        setState(() => _isSending = false);
        _scrollToBottom();
      }
    }
  }

  void _replaceMessage(String oldId, ChatMessage nextMessage) {
    if (!mounted) {
      return;
    }

    setState(() {
      final index = _messages.indexWhere((message) => message.id == oldId);
      if (index == -1) {
        _messages.add(nextMessage);
      } else {
        _messages[index] = nextMessage;
      }
    });
  }

  void _retry(ChatMessage message) {
    final question = message.retryQuestion;
    if (question == null || _isSending) {
      return;
    }

    setState(() {
      _messages.removeWhere((item) => item.id == message.id);
    });
    _sendMessage(question, addUserMessage: false);
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_scrollController.hasClients) {
        return;
      }

      _scrollController.animateTo(
        _scrollController.position.maxScrollExtent,
        duration: const Duration(milliseconds: 260),
        curve: Curves.easeOutCubic,
      );
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Column(
        children: [
          const _ChatHeader(),
          Expanded(
            child: ListView(
              controller: _scrollController,
              padding: const EdgeInsets.fromLTRB(16, 14, 16, 18),
              children: [
                if (!_hasUserMessages) const _EmptyState(),
                for (final message in _messages)
                  MessageBubble(
                    message: message,
                    onRetry: message.isError ? () => _retry(message) : null,
                  ),
              ],
            ),
          ),
          const _DisclaimerCard(),
          ChatInputBar(isSending: _isSending, onSend: _sendMessage),
        ],
      ),
    );
  }
}

class _ChatHeader extends StatelessWidget {
  const _ChatHeader();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: EdgeInsets.fromLTRB(
        18,
        MediaQuery.paddingOf(context).top + 14,
        18,
        18,
      ),
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topRight,
          end: Alignment.bottomLeft,
          colors: [AppTheme.navy, AppTheme.deepBlue],
        ),
        borderRadius: BorderRadius.vertical(bottom: Radius.circular(26)),
      ),
      child: Row(
        children: [
          Container(
            width: 56,
            height: 56,
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(18),
              border: Border.all(color: Colors.white.withValues(alpha: 0.18)),
            ),
            child: const Icon(
              Icons.balance_rounded,
              color: Colors.white,
              size: 30,
            ),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Directionality(
                  textDirection: TextDirection.ltr,
                  child: Text(
                    'Lmo7ami AI',
                    style: Theme.of(context).textTheme.titleLarge?.copyWith(
                      color: Colors.white,
                      fontWeight: FontWeight.w900,
                      letterSpacing: 0,
                    ),
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  'مساعد قانون الشغل المغربي',
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: Colors.white.withValues(alpha: 0.82),
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
            ),
          ),
          Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
              color: AppTheme.emerald.withValues(alpha: 0.18),
              borderRadius: BorderRadius.circular(14),
            ),
            child: const Icon(
              Icons.gavel_rounded,
              color: Colors.white,
              size: 22,
            ),
          ),
        ],
      ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState();

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(22),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.05),
            blurRadius: 18,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              _IconTile(
                icon: Icons.description_rounded,
                color: AppTheme.deepBlue,
                backgroundColor: const Color(0xFFEAF1F8),
              ),
              const SizedBox(width: 10),
              _IconTile(
                icon: Icons.balance_rounded,
                color: const Color(0xFF047857),
                backgroundColor: const Color(0xFFE6F8F1),
              ),
              const SizedBox(width: 10),
              _IconTile(
                icon: Icons.chat_rounded,
                color: const Color(0xFF7C3AED),
                backgroundColor: const Color(0xFFF1ECFE),
              ),
            ],
          ),
          const SizedBox(height: 14),
          Text(
            'سول على حقوقك فالشغل',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
              color: AppTheme.textPrimary,
              fontWeight: FontWeight.w900,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            'أمثلة: الطرد، العطلة السنوية، العقد، التعويضات، ساعات العمل، أو حقوق الأجير.',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
              color: AppTheme.textMuted,
              height: 1.5,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}

class _IconTile extends StatelessWidget {
  const _IconTile({
    required this.icon,
    required this.color,
    required this.backgroundColor,
  });

  final IconData icon;
  final Color color;
  final Color backgroundColor;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 46,
      height: 46,
      decoration: BoxDecoration(
        color: backgroundColor,
        borderRadius: BorderRadius.circular(15),
      ),
      child: Icon(icon, color: color, size: 24),
    );
  }
}

class _DisclaimerCard extends StatelessWidget {
  const _DisclaimerCard();

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        decoration: BoxDecoration(
          color: AppTheme.navy.withValues(alpha: 0.05),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: AppTheme.navy.withValues(alpha: 0.08)),
        ),
        child: Row(
          children: [
            const Icon(
              Icons.info_outline_rounded,
              color: AppTheme.textMuted,
              size: 18,
            ),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                'هاد المساعد كيعطي معلومات عامة فقط، وماشي استشارة قانونية رسمية.',
                style: Theme.of(context).textTheme.labelMedium?.copyWith(
                  color: AppTheme.textMuted,
                  height: 1.35,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
