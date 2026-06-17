# 🎮 Laberinto Android — Kivy

Juego de laberinto con generación procedural, niebla de guerra y power-ups.  
**Sin pygame. Sin errores de Buildozer.** Kivy puro = APK estable.

## Estructura del proyecto

```
laberinto_kivy/
├── main.py              ← Juego completo
├── buildozer.spec       ← Config compilación APK
└── LaberintoAndroid.ipynb  ← Notebook Colab para compilar
```

## Probar en PC primero

```bash
pip install kivy
python main.py
```

Controles PC: `WASD` o flechas.

## Compilar APK en Google Colab

1. Sube la carpeta a tu Google Drive o clona el repo en Colab.
2. Abre `LaberintoAndroid.ipynb` en Colab.
3. Ejecuta las celdas **en orden** (1 → 7).
4. La celda 7 descarga el `.apk` directamente.

> La primera compilación tarda **15–30 minutos** porque descarga Android SDK/NDK.  
> Las siguientes compilaciones son más rápidas (caché en `/root/.buildozer`).

## Subir a GitHub

```bash
git init
git add main.py buildozer.spec LaberintoAndroid.ipynb README.md
git commit -m "Laberinto Kivy v1.0 - Android"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/laberinto-android.git
git push -u origin main
```

## Características

- ✅ Laberinto procedural (DFS backtracker)
- ✅ Niebla de guerra
- ✅ Power-ups: velocidad y visión
- ✅ D-pad táctil para Android
- ✅ Multi-nivel con colores diferentes
- ✅ Detección de colisión círculo-AABB
- ✅ Sin pygame — Kivy nativo Android

## Por qué Kivy y no pygame+Buildozer

| | pygame + Buildozer | Kivy + Buildozer |
|---|---|---|
| Errores de compilación | Muchos | Mínimos |
| Soporte Android oficial | No | Sí |
| Dependencias conflictivas | Sí | No |
| APK estable | Difícil | Sí |
