import 'package:flutter/material.dart';

import '../models/chat_message.dart';
import '../theme/app_theme.dart';
import 'source_chip.dart';

class MessageBubble extends StatelessWidget {
  const MessageBubble({required this.message, this.onRetry, super.key});

  final ChatMessage message;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    final maxWidth = MediaQuery.sizeOf(context).width * 0.78;
    final isUser = message.isUser;
    final backgroundColor = isUser
        ? AppTheme.deepBlue
        : message.isError
        ? const Color(0xFFFFF1F2)
        : Colors.white;
    final foregroundColor = isUser
        ? Colors.white
        : message.isError
        ? const Color(0xFF9F1239)
        : AppTheme.textPrimary;

    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: ConstrainedBox(
        constraints: BoxConstraints(maxWidth: maxWidth),
        child: Container(
          margin: const EdgeInsets.symmetric(vertical: 6),
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: backgroundColor,
            borderRadius: BorderRadius.only(
              topLeft: const Radius.circular(20),
              topRight: const Radius.circular(20),
              bottomLeft: Radius.circular(isUser ? 20 : 6),
              bottomRight: Radius.circular(isUser ? 6 : 20),
            ),
            border: message.isError
                ? Border.all(color: const Color(0xFFFDA4AF))
                : null,
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.06),
                blurRadius: 16,
                offset: const Offset(0, 8),
              ),
            ],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (message.isLoading)
                _LoadingAnswer(color: foregroundColor)
              else
                SelectableText(
                  message.text,
                  textDirection: TextDirection.rtl,
                  textAlign: TextAlign.right,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: foregroundColor,
                    height: 1.55,
                    fontWeight: isUser ? FontWeight.w700 : FontWeight.w500,
                  ),
                ),
              if (message.sources.isNotEmpty) ...[
                const SizedBox(height: 12),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    for (final source in message.sources)
                      SourceChip(source: source),
                  ],
                ),
              ],
              if (message.isError && onRetry != null) ...[
                const SizedBox(height: 12),
                OutlinedButton.icon(
                  onPressed: onRetry,
                  icon: const Icon(Icons.refresh_rounded, size: 18),
                  label: const Text('عاود جرّب'),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: const Color(0xFF9F1239),
                    side: const BorderSide(color: Color(0xFFFDA4AF)),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(14),
                    ),
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _LoadingAnswer extends StatelessWidget {
  const _LoadingAnswer({required this.color});

  final Color color;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        SizedBox(
          width: 18,
          height: 18,
          child: CircularProgressIndicator(
            strokeWidth: 2.4,
            color: AppTheme.emerald,
            backgroundColor: AppTheme.emerald.withValues(alpha: 0.16),
          ),
        ),
        const SizedBox(width: 10),
        Text(
          'كنقلب فالمصادر القانونية...',
          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
            color: color,
            fontWeight: FontWeight.w700,
          ),
        ),
      ],
    );
  }
}
