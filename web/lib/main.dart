import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:drum_trainer_web/screens/home_screen.dart';
import 'package:drum_trainer_web/services/api_service.dart';
import 'package:drum_trainer_web/services/audio_service.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const DrumTrainerApp());
}

class DrumTrainerApp extends StatelessWidget {
  const DrumTrainerApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        Provider(create: (_) => ApiService()),
        ChangeNotifierProvider(create: (_) => AudioService()),
      ],
      child: MaterialApp(
        title: '🥁 Drum Trainer',
        debugShowCheckedModeBanner: false,
        theme: ThemeData(
          brightness: Brightness.dark,
          primarySwatch: Colors.deepPurple,
          scaffoldBackgroundColor: const Color(0xFF0A0A0F),
          appBarTheme: const AppBarTheme(
            backgroundColor: Color(0xFF12121A),
            elevation: 1,
          ),
          cardTheme: CardTheme(
            backgroundColor: const Color(0xFF1A1A24).withOpacity(0.5),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(16),
              side: BorderSide(
                color: const Color(0xFFFFFFFF).withOpacity(0.08),
              ),
            ),
          ),
          textTheme: const TextTheme(
            headlineLarge: TextStyle(
              fontWeight: FontWeight.w700,
              letterSpacing: -0.02,
            ),
            bodyLarge: TextStyle(
              color: Color(0xFFCBD5E1),
            ),
            bodyMedium: TextStyle(
              color: Color(0xFF94A3B8),
            ),
          ),
          inputDecorationTheme: InputDecorationTheme(
            filled: true,
            fillColor: const Color(0xFF1A1A24).withOpacity(0.5),
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12),
              borderSide: BorderSide(
                color: const Color(0xFFFFFFFF).withOpacity(0.08),
              ),
            ),
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12),
              borderSide: BorderSide(
                color: const Color(0xFFFFFFFF).withOpacity(0.08),
              ),
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12),
              borderSide: BorderSide(
                color: Colors.deepPurple.shade400,
                width: 2,
              ),
            ),
          ),
          elevatedButtonTheme: ElevatedButtonThemeData(
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.deepPurple.shade600,
              foregroundColor: Colors.white,
              padding: const EdgeInsets.symmetric(
                horizontal: 24,
                vertical: 16,
              ),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
              ),
              elevation: 4,
            ),
          ),
        ),
        home: const HomeScreen(),
      ),
    );
  }
}
