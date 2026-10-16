// Habits para Android: abre la app web (https://habits.proyecto.lol) a pantalla
// completa, con subida de fotos y apuntes, descargas, botón atrás y recargar.
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_inappwebview/flutter_inappwebview.dart';
import 'package:url_launcher/url_launcher.dart';

/// Dirección de la app web. Cámbiala si usas otro dominio.
const String urlInicio = 'https://habits.proyecto.lol/';
const Color morado = Color(0xFF7B2FF7);
const Color fondo = Color(0xFF0A0012);

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  SystemChrome.setSystemUIOverlayStyle(const SystemUiOverlayStyle(
    statusBarColor: fondo,
    statusBarIconBrightness: Brightness.light,
    systemNavigationBarColor: fondo,
    systemNavigationBarIconBrightness: Brightness.light,
  ));
  runApp(const HabitsApp());
}

class HabitsApp extends StatelessWidget {
  const HabitsApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Habits',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: morado, brightness: Brightness.dark),
        scaffoldBackgroundColor: fondo,
      ),
      home: const PantallaWeb(),
    );
  }
}

class PantallaWeb extends StatefulWidget {
  const PantallaWeb({super.key});

  @override
  State<PantallaWeb> createState() => _PantallaWebState();
}

class _PantallaWebState extends State<PantallaWeb> {
  InAppWebViewController? _web;
  PullToRefreshController? _recargar;
  double _progreso = 0;
  bool _sinConexion = false;

  final String _host = Uri.parse(urlInicio).host;

  @override
  void initState() {
    super.initState();
    _recargar = PullToRefreshController(
      settings: PullToRefreshSettings(color: morado),
      onRefresh: () async => _web?.reload(),
    );
  }

  bool _esDeLaApp(Uri? url) =>
      url != null && (url.host == _host || url.host == 'www.$_host');

  Future<void> _abrirAfuera(Uri url) async {
    await launchUrl(url, mode: LaunchMode.externalApplication);
  }

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: false,
      // El botón atrás del celular navega hacia atrás dentro de la app
      onPopInvokedWithResult: (didPop, _) async {
        if (didPop) return;
        if (_web != null && await _web!.canGoBack()) {
          _web!.goBack();
        } else {
          SystemNavigator.pop();
        }
      },
      child: Scaffold(
        body: SafeArea(
          child: Stack(
            children: [
              InAppWebView(
                initialUrlRequest: URLRequest(url: WebUri(urlInicio)),
                pullToRefreshController: _recargar,
                initialSettings: InAppWebViewSettings(
                  javaScriptEnabled: true,
                  domStorageEnabled: true,
                  useShouldOverrideUrlLoading: true,
                  useOnDownloadStart: true,
                  mediaPlaybackRequiresUserGesture: false,
                  allowFileAccess: false,
                  supportZoom: false,
                  transparentBackground: true,
                  applicationNameForUserAgent: 'HabitsApp',
                ),
                onWebViewCreated: (c) => _web = c,
                // Enlaces de otros sitios se abren en el navegador del celular
                shouldOverrideUrlLoading: (c, accion) async {
                  final url = accion.request.url;
                  if (url == null || _esDeLaApp(url) || url.scheme == 'about') {
                    return NavigationActionPolicy.ALLOW;
                  }
                  await _abrirAfuera(url);
                  return NavigationActionPolicy.CANCEL;
                },
                // Descargas (por ejemplo, tus apuntes): se abren con el navegador
                onDownloadStartRequest: (c, pedido) => _abrirAfuera(pedido.url),
                onProgressChanged: (c, p) {
                  setState(() => _progreso = p / 100);
                  if (p == 100) _recargar?.endRefreshing();
                },
                onLoadStop: (c, url) {
                  _recargar?.endRefreshing();
                  setState(() => _sinConexion = false);
                },
                onReceivedError: (c, pedido, error) {
                  _recargar?.endRefreshing();
                  if (pedido.isForMainFrame ?? false) {
                    setState(() => _sinConexion = true);
                  }
                },
              ),
              if (_progreso < 1)
                LinearProgressIndicator(
                  value: _progreso,
                  minHeight: 3,
                  color: morado,
                  backgroundColor: Colors.transparent,
                ),
              if (_sinConexion) _SinConexion(onReintentar: () => _web?.reload()),
            ],
          ),
        ),
      ),
    );
  }
}

class _SinConexion extends StatelessWidget {
  const _SinConexion({required this.onReintentar});
  final VoidCallback onReintentar;

  @override
  Widget build(BuildContext context) {
    return Container(
      color: fondo,
      alignment: Alignment.center,
      padding: const EdgeInsets.all(24),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          ClipRRect(
            borderRadius: BorderRadius.circular(24),
            child: Image.asset('assets/icon/icono.png', width: 96, height: 96),
          ),
          const SizedBox(height: 20),
          const Text('Sin conexión',
              style: TextStyle(fontSize: 24, fontStyle: FontStyle.italic, color: Color(0xFFD966FF))),
          const SizedBox(height: 8),
          const Text('Revisa tu internet. Tus hábitos te esperan.',
              textAlign: TextAlign.center, style: TextStyle(color: Colors.white70)),
          const SizedBox(height: 22),
          FilledButton(
            onPressed: onReintentar,
            style: FilledButton.styleFrom(backgroundColor: morado),
            child: const Text('Reintentar'),
          ),
        ],
      ),
    );
  }
}
