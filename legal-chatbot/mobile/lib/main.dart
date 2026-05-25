import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';

import 'screens/splash_screen.dart';
import 'theme/app_theme.dart';

void main() {
  runApp(const Lmo7amiApp());
}

class Lmo7amiApp extends StatelessWidget {
  const Lmo7amiApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Lmo7ami AI',
      debugShowCheckedModeBanner: false,
      locale: const Locale('ar'),
      supportedLocales: const [Locale('ar'), Locale('fr'), Locale('en')],
      localizationsDelegates: const [
        GlobalMaterialLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
      ],
      theme: AppTheme.lightTheme,
      darkTheme: AppTheme.darkTheme,
      themeMode: ThemeMode.system,
      builder: (context, child) {
        return Directionality(
          textDirection: TextDirection.rtl,
          child: child ?? const SizedBox.shrink(),
        );
      },
      home: const SplashScreen(),
    );
  }
}
