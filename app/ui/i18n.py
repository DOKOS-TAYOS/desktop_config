from __future__ import annotations

from typing import Literal


LanguageCode = Literal["es", "en"]

TRANSLATIONS: dict[LanguageCode, dict[str, str]] = {
    "es": {
        "app.title": "SunSetup Planner",
        "language.label": "Idioma / Language",
        "header.subtitle": (
            "Decide si tu escritorio funciona mejor por la mañana o por la tarde "
            "sin promesas mágicas."
        ),
        "header.description": (
            "La app estima reflejos, calor directo y confort ergonómico con un modelo "
            "geométrico simple, explicable y pensado para decisiones reales de teletrabajo."
        ),
        "sidebar.context": "Contexto del escenario",
        "sidebar.caption": "La distribución principal se edita en el plano 2D del panel central.",
        "sidebar.presets": "Presets útiles",
        "sidebar.room": "Habitación",
        "sidebar.window": "Ventana",
        "sidebar.monitor": "Monitor",
        "sidebar.desk_layout": "Distribución de la mesa",
        "sidebar.apply_presets": "Aplicar presets",
        "sidebar.location_and_date": "Ubicación y fecha",
        "sidebar.mode": "Modo",
        "sidebar.mode.city": "Ciudad",
        "sidebar.mode.manual": "Manual",
        "sidebar.city_query": "Ciudad o ciudad, país",
        "sidebar.timezone": "Zona horaria IANA",
        "sidebar.analysis_date": "Fecha de análisis",
        "sidebar.use_live_weather": "Intentar clima real con Open-Meteo",
        "sidebar.include_seasonal_summary": "Añadir resumen estacional",
        "sidebar.advanced_controls": "Ajuste numérico avanzado",
        "sidebar.advanced_caption": "Úsalo como apoyo o para hacer ajustes finos cuando lo necesites.",
        "sidebar.run_analysis": "Actualizar análisis",
        "summary.whats_happening": "Qué está pasando",
        "summary.good_hours": "Horas buenas",
        "summary.conflict_hours": "Horas conflictivas",
        "summary.first_adjustment": "Qué tocar primero",
        "summary.confidence": "Confianza del análisis",
        "summary.no_data": "Sin datos suficientes.",
        "summary.metric.comfort": "Confort",
        "summary.metric.glare": "Riesgo de reflejo",
        "summary.metric.heat": "Riesgo térmico",
        "summary.metric.ergonomics": "Riesgo ergonómico",
        "summary.weather.forecast": "Clima real con Open-Meteo",
        "summary.weather.theoretical": "Cielo despejado teórico",
        "summary.weather.caption": "Ubicación resuelta: {location}. Modo de clima: {weather_mode}.",
        "summary.glare_window": "Reflejo alto en: {window_list}",
        "summary.heat_window": "Calor alto en: {window_list}",
        "summary.section.timeline": "Evolución del día",
        "summary.section.recommendation": "Antes y recomendación",
        "summary.section.actions": "Cambios accionables",
        "summary.section.plan": "Plano 2D y dirección solar",
        "summary.section.seasonal": "Resumen estacional",
        "summary.section.compare": "Comparador actual frente a recomendado",
        "summary.fallback_editor": "El editor no está disponible en esta sesión. Puedes seguir ajustando el escenario desde la barra lateral.",
        "summary.empty_state": "Ajusta el escenario en la barra lateral o en el plano y pulsa Actualizar análisis.",
        "summary.pending_changes": "Hay cambios pendientes. El plano ya está actualizado, pero el análisis mostrado corresponde al último cálculo guardado.",
        "summary.recommendation.none": "Sin recomendación disponible.",
        "summary.recommendation.no_change": "La configuración actual ya está bastante equilibrada para este modelo.",
        "summary.recommendation.move": "Desplaza la mesa {distance_cm} cm hacia el {direction}.",
        "summary.recommendation.rotate_desk": "Gira la mesa {degrees}° {direction}.",
        "summary.recommendation.rotate_monitor": "Ajusta el monitor {degrees}° {direction}.",
        "summary.recommendation.reason.material": "Reduce el riesgo dominante y mejora el confort total.",
        "summary.recommendation.reason.marginal": "La mejor variante encontrada no reduce el riesgo dominante de forma material.",
        "summary.direction.east": "este",
        "summary.direction.west": "oeste",
        "summary.direction.north": "norte",
        "summary.direction.south": "sur",
        "summary.direction.left": "a la izquierda",
        "summary.direction.right": "a la derecha",
        "summary.season.best_worst": "Mejor estación media: {best_label} ({best_score:.1f}/100). Peor estación media: {worst_label} ({worst_score:.1f}/100).",
        "summary.config.current": "Configuración actual",
        "summary.config.recommended": "Configuración recomendada",
        "summary.config.desk_position": "Mesa en ({x:.2f}, {y:.2f}) m",
        "summary.config.desk_orientation": "Orientación de la mesa: {degrees:.0f}°",
        "summary.config.monitor_orientation": "Orientación del monitor: {degrees:.0f}°",
        "summary.model_notes": "Cómo interpreta el modelo",
        "summary.model_note.1": "La planta se modela en 2D con una habitación rectangular y una ventana principal.",
        "summary.model_note.2": "La parte vertical es una simplificación: se usan alturas de mesa, monitor y ojos para estimar incidencia solar.",
        "summary.model_note.3": "El riesgo de reflejo se clasifica con heurísticas geométricas; no es una simulación óptica científica.",
        "summary.model_note.4": "El clima real solo se usa cuando Open-Meteo tiene datos disponibles para esa fecha. Si no, se calcula con cielo despejado teórico.",
        "editor.hint": "Los cambios del plano quedan listos para el siguiente análisis manual.",
        "editor.hint.dragging": "Al soltar el ratón se guardará el ajuste en el plano.",
        "editor.hint.commit": "Cambio aplicado. Pulsa Actualizar análisis para recalcular.",
        "editor.title": "Editor 2D interactivo",
        "editor.subtitle": "Mueve, gira y redimensiona la habitación, la mesa y la ventana desde el propio plano.",
        "editor.legend.window": "Ventana",
        "editor.legend.desk": "Mesa",
        "editor.legend.monitor": "Monitor",
        "editor.legend.handles": "Asas de giro y tamaño",
        "editor.room": "Habitación",
        "editor.desk": "Mesa",
        "editor.monitor": "Monitor",
        "editor.window": "Ventana",
        "season.invierno": "Invierno",
        "season.primavera": "Primavera",
        "season.verano": "Verano",
        "season.otono": "Otoño",
        "window_label.morning": "mañana",
        "window_label.midday": "mediodía",
        "window_label.afternoon": "tarde",
        "window_label.late_hours": "últimas horas",
    },
    "en": {
        "app.title": "SunSetup Planner",
        "language.label": "Idioma / Language",
        "header.subtitle": (
            "Decide whether your desk works better in the morning or in the afternoon "
            "without fake precision."
        ),
        "header.description": (
            "The app estimates glare, direct solar heat, and ergonomic comfort with a "
            "simple geometric model designed for real home-office decisions."
        ),
        "sidebar.context": "Scenario context",
        "sidebar.caption": "The main layout is edited in the 2D floor plan in the center panel.",
        "sidebar.presets": "Useful presets",
        "sidebar.room": "Room",
        "sidebar.window": "Window",
        "sidebar.monitor": "Monitor",
        "sidebar.desk_layout": "Desk layout",
        "sidebar.apply_presets": "Apply presets",
        "sidebar.location_and_date": "Location and date",
        "sidebar.mode": "Mode",
        "sidebar.mode.city": "City",
        "sidebar.mode.manual": "Manual",
        "sidebar.city_query": "City or city, country",
        "sidebar.timezone": "IANA time zone",
        "sidebar.analysis_date": "Analysis date",
        "sidebar.use_live_weather": "Try real weather with Open-Meteo",
        "sidebar.include_seasonal_summary": "Include seasonal summary",
        "sidebar.advanced_controls": "Advanced numeric adjustments",
        "sidebar.advanced_caption": "Use this as a fallback or for finer manual adjustments.",
        "sidebar.run_analysis": "Update analysis",
        "summary.whats_happening": "What is happening",
        "summary.good_hours": "Good hours",
        "summary.conflict_hours": "Problem hours",
        "summary.first_adjustment": "What to adjust first",
        "summary.confidence": "Analysis confidence",
        "summary.no_data": "Not enough data.",
        "summary.metric.comfort": "Comfort",
        "summary.metric.glare": "Glare risk",
        "summary.metric.heat": "Heat risk",
        "summary.metric.ergonomics": "Ergonomic risk",
        "summary.weather.forecast": "Real weather with Open-Meteo",
        "summary.weather.theoretical": "Theoretical clear sky",
        "summary.weather.caption": "Resolved location: {location}. Weather mode: {weather_mode}.",
        "summary.glare_window": "High glare at: {window_list}",
        "summary.heat_window": "High heat at: {window_list}",
        "summary.section.timeline": "Day timeline",
        "summary.section.recommendation": "Current vs recommendation",
        "summary.section.actions": "Actionable changes",
        "summary.section.plan": "2D floor plan and solar direction",
        "summary.section.seasonal": "Seasonal summary",
        "summary.section.compare": "Current vs recommended comparison",
        "summary.fallback_editor": "The editor is not available in this session. You can keep adjusting the scenario from the sidebar.",
        "summary.empty_state": "Adjust the scenario in the sidebar or on the floor plan, then press Update analysis.",
        "summary.pending_changes": "There are pending changes. The floor plan is up to date, but the analysis still reflects the last saved calculation.",
        "summary.recommendation.none": "No recommendation available.",
        "summary.recommendation.no_change": "The current layout is already fairly balanced for this model.",
        "summary.recommendation.move": "Move the desk {distance_cm} cm toward the {direction}.",
        "summary.recommendation.rotate_desk": "Rotate the desk {degrees}° {direction}.",
        "summary.recommendation.rotate_monitor": "Adjust the monitor {degrees}° {direction}.",
        "summary.recommendation.reason.material": "It reduces the dominant risk and improves overall comfort.",
        "summary.recommendation.reason.marginal": "The best variant found does not reduce the dominant risk in a meaningful way.",
        "summary.direction.east": "east",
        "summary.direction.west": "west",
        "summary.direction.north": "north",
        "summary.direction.south": "south",
        "summary.direction.left": "to the left",
        "summary.direction.right": "to the right",
        "summary.season.best_worst": "Best average season: {best_label} ({best_score:.1f}/100). Worst average season: {worst_label} ({worst_score:.1f}/100).",
        "summary.config.current": "Current layout",
        "summary.config.recommended": "Recommended layout",
        "summary.config.desk_position": "Desk at ({x:.2f}, {y:.2f}) m",
        "summary.config.desk_orientation": "Desk orientation: {degrees:.0f}°",
        "summary.config.monitor_orientation": "Monitor orientation: {degrees:.0f}°",
        "summary.model_notes": "How the model works",
        "summary.model_note.1": "The floor plan is modeled in 2D with a rectangular room and one main window.",
        "summary.model_note.2": "The vertical part is simplified: desk, monitor, and eye heights are used to estimate solar incidence.",
        "summary.model_note.3": "Glare risk is classified with geometric heuristics; it is not a scientific optical simulation.",
        "summary.model_note.4": "Real weather is only used when Open-Meteo has data available for that date. Otherwise, the app falls back to a theoretical clear-sky model.",
        "editor.hint": "Floor-plan changes are ready for the next manual analysis.",
        "editor.hint.dragging": "Releasing the mouse stores the adjustment on the floor plan.",
        "editor.hint.commit": "Change applied. Press Update analysis to recalculate.",
        "editor.title": "Interactive 2D editor",
        "editor.subtitle": "Move, rotate, and resize the room, desk, and window directly on the floor plan.",
        "editor.legend.window": "Window",
        "editor.legend.desk": "Desk",
        "editor.legend.monitor": "Monitor",
        "editor.legend.handles": "Rotation and resize handles",
        "editor.room": "Room",
        "editor.desk": "Desk",
        "editor.monitor": "Monitor",
        "editor.window": "Window",
        "season.invierno": "Winter",
        "season.primavera": "Spring",
        "season.verano": "Summer",
        "season.otono": "Autumn",
        "window_label.morning": "morning",
        "window_label.midday": "midday",
        "window_label.afternoon": "afternoon",
        "window_label.late_hours": "late hours",
    },
}

PRESET_TRANSLATIONS: dict[str, dict[str, str]] = {
    "room": {
        "Despacho estándar": "Standard home office",
        "Despacho compacto": "Compact home office",
        "Dormitorio pequeño": "Small bedroom",
        "Dormitorio principal": "Main bedroom",
        "Salón adaptado": "Adapted living room",
        "Habitación alargada": "Long narrow room",
    },
    "desk_layout": {
        "Centrado": "Centered",
        "Pegado a pared": "Against the wall",
    },
    "window": {
        "Norte": "North",
        "Este": "East",
        "Sur": "South",
        "Oeste": "West",
    },
}


def translate(key: str, language: LanguageCode, **kwargs: object) -> str:
    template = TRANSLATIONS.get(language, TRANSLATIONS["es"]).get(key)
    if template is None:
        template = TRANSLATIONS["es"].get(key, key)
    try:
        return template.format(**kwargs)
    except (IndexError, KeyError, ValueError):
        return template


def translate_compass(value: int, language: LanguageCode) -> str:
    key_map = {0: "Norte", 90: "Este", 180: "Sur", 270: "Oeste"}
    base_label = key_map[value]
    if language == "es":
        return base_label
    return PRESET_TRANSLATIONS["window"].get(base_label, base_label)


def translate_preset(category: str, label: str, language: LanguageCode) -> str:
    if language == "es":
        return label
    return PRESET_TRANSLATIONS.get(category, {}).get(label, label)


def translate_window_label(label: str, language: LanguageCode) -> str:
    normalized = label.strip().lower()
    mapping = {
        "mañana": "window_label.morning",
        "manana": "window_label.morning",
        "mediodía": "window_label.midday",
        "mediodia": "window_label.midday",
        "tarde": "window_label.afternoon",
        "últimas horas": "window_label.late_hours",
        "ultimas horas": "window_label.late_hours",
    }
    key = mapping.get(normalized)
    return translate(key, language) if key else label


def translate_season(season: str, language: LanguageCode) -> str:
    return translate(f"season.{season}", language)
