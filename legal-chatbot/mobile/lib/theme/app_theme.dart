import 'package:flutter/material.dart';

class AppTheme {
  AppTheme._();

  static const Color navy = Color(0xFF0B1F3A);
  static const Color deepBlue = Color(0xFF123B64);
  static const Color emerald = Color(0xFF10B981);
  static const Color lightBackground = Color(0xFFF6F8FB);
  static const Color darkBackground = Color(0xFF0F172A);
  static const Color cardSurface = Color(0xFFFFFFFF);
  static const Color textPrimary = Color(0xFF172033);
  static const Color textMuted = Color(0xFF667085);

  static ThemeData get lightTheme {
    final colorScheme = ColorScheme.fromSeed(
      seedColor: deepBlue,
      primary: navy,
      secondary: emerald,
      surface: cardSurface,
      brightness: Brightness.light,
    );

    return ThemeData(
      useMaterial3: true,
      colorScheme: colorScheme,
      scaffoldBackgroundColor: lightBackground,
      fontFamily: 'Roboto',
      appBarTheme: const AppBarTheme(
        backgroundColor: Colors.transparent,
        foregroundColor: textPrimary,
        elevation: 0,
        centerTitle: false,
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: Colors.white,
        hintStyle: const TextStyle(color: textMuted),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(22),
          borderSide: BorderSide.none,
        ),
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 16,
          vertical: 14,
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: emerald,
          foregroundColor: Colors.white,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(18),
          ),
        ),
      ),
      chipTheme: ChipThemeData(
        backgroundColor: emerald.withValues(alpha: 0.10),
        labelStyle: const TextStyle(
          color: Color(0xFF047857),
          fontWeight: FontWeight.w700,
        ),
        side: BorderSide(color: emerald.withValues(alpha: 0.22)),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(999)),
      ),
    );
  }

  static ThemeData get darkTheme {
    final colorScheme = ColorScheme.fromSeed(
      seedColor: emerald,
      primary: emerald,
      secondary: deepBlue,
      surface: const Color(0xFF111827),
      brightness: Brightness.dark,
    );

    return ThemeData(
      useMaterial3: true,
      colorScheme: colorScheme,
      scaffoldBackgroundColor: darkBackground,
      fontFamily: 'Roboto',
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: const Color(0xFF1F2937),
        hintStyle: const TextStyle(color: Color(0xFFCBD5E1)),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(22),
          borderSide: BorderSide.none,
        ),
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 16,
          vertical: 14,
        ),
      ),
      chipTheme: ChipThemeData(
        backgroundColor: emerald.withValues(alpha: 0.16),
        labelStyle: const TextStyle(
          color: Color(0xFFA7F3D0),
          fontWeight: FontWeight.w700,
        ),
        side: BorderSide(color: emerald.withValues(alpha: 0.32)),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(999)),
      ),
    );
  }
}
