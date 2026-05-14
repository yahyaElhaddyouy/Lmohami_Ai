import 'package:flutter/material.dart';

import '../models/chat_response.dart';
import '../theme/app_theme.dart';

class SourceChip extends StatelessWidget {
  const SourceChip({required this.source, super.key});

  final ChatSource source;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: AppTheme.emerald.withValues(alpha: 0.10),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: AppTheme.emerald.withValues(alpha: 0.22)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(
            Icons.description_rounded,
            size: 15,
            color: Color(0xFF047857),
          ),
          const SizedBox(width: 6),
          Text(
            'المصدر ${source.number} - الصفحة ${source.page}',
            style: Theme.of(context).textTheme.labelMedium?.copyWith(
              color: const Color(0xFF047857),
              fontWeight: FontWeight.w800,
            ),
          ),
        ],
      ),
    );
  }
}
