// app/camera.tsx
import { MaterialIcons } from "@expo/vector-icons";
import { CameraView, useCameraPermissions } from "expo-camera";
import * as Haptics from "expo-haptics";
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Alert,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  View,
  useWindowDimensions,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useRouter } from "expo-router";
import { useLocalSearchParams } from "expo-router";

import ModelWebView from "../src/components/ModelWebView";
import { API_BASE } from "../src/config";
import { getTTSService, RiskLevel } from "../src/services/TTSService";
import { getSTTService } from "../src/services/STTService";
import HomeHeader from "./HomeHeader";
import Footer from "./Footer";

const tokens = {
  bg: "#0D1B2A",
  card: "#111",
  gold: "#FCA311",
  text: "#E0E1DD",
};

// Auto Scan configuration constants
const AUTO_SCAN_INTERVAL_MS = 8000;
const AUTO_SCAN_TIMEOUT_MS = 25000;

type Mode = "idle" | "vision" | "voice" | "ocr";

export default function CameraAssistScreen() {
  const router = useRouter();
  const { width, height } = useWindowDimensions();

  const contentWidth = useMemo(() => {
    const padding = 24;
    const max = 720;
    return Math.min(max, Math.max(320, width - padding * 2));
  }, [width]);

  // default mode = voice (camera only, no Gradio)
  const [mode, setMode] = useState<Mode>("voice");

  // TTS service (force speak in autoscan)
  // FIX: Store TTS in useMemo to prevent recreation on every render
  // Auto-scan only ran once because tts was recreated, causing captureAndProcess to be recreated, breaking the interval
  const tts = useMemo(() => getTTSService({ cooldownSeconds: 0 }), []);

  // camera for voice assist
  const [perm, requestPermission] = useCameraPermissions();
  const cameraRef = useRef<CameraView>(null);

  // WebView state
  const [loading, setLoading] = useState(false);
  const [rev, setRev] = useState(0);

  // Pick the correct mounted Gradio app
  const url = useMemo(() => {
    if (mode === "vision") return `${API_BASE}/vision/?v=${rev}`;
    if (mode === "ocr") return `${API_BASE}/ocr/?v=${rev}`;
    return "";
  }, [mode, rev]);

  // simple loading state when switching between modes
  useEffect(() => {
    if (mode === "vision" || mode === "ocr") {
      setLoading(true);
      setRev((x) => x + 1);
      const t = setTimeout(() => setLoading(false), 800);
      return () => clearTimeout(t);
    }
    setLoading(false);
  }, [mode]);

  // voice assist
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [sttAvailable, setSttAvailable] = useState(false);
  const [isVoiceProcessing, setIsVoiceProcessing] = useState(false); // Separate from scan state
  const sttService = getSTTService({ language: "en-US" });

  // auto scan state
  const [isAutoScanning, setIsAutoScanning] = useState(false);
  const isRequestInFlight = useRef(false);
  const scanIntervalRef = useRef<number | null>(null);
  // Deduplication: track last spoken message to avoid repeating same announcements
  const lastSpokenMessage = useRef<string>("");
  const lastSpokenTime = useRef<number>(0);

  // STT availability check
  useEffect(() => {
    setSttAvailable(sttService.isAvailable());
  }, []);

  // --------- voice assist ----------
  const processQuery = useCallback(async (queryText: string) => {
    if (!queryText.trim()) return;

    setIsVoiceProcessing(true);
    try {
      // Add timeout to prevent voice commands from hanging
      // Auto-scan broke because network calls could hang indefinitely, blocking the scan loop
      // Fix: Use AbortController with 9-second timeout to ensure voice processing never blocks scanning
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 9000);

      let response: Response;
      try {
        response = await fetch(`${API_BASE}/query`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ query: queryText }),
          signal: controller.signal,
        });
        clearTimeout(timeoutId);
      } catch (fetchError: any) {
        clearTimeout(timeoutId);
        if (fetchError.name === 'AbortError') {
          throw new Error("Request timed out. Please check your network connection.");
        }
        throw fetchError;
      }

      if (!response.ok) {
        throw new Error(`Query failed: ${response.status}`);
      }

      const data = await response.json();
      const ttsMessage = data.tts_message || data.response || "Query processed";

      // Speak the response using TTS
      await tts.speak(ttsMessage, RiskLevel.LOW, true);
    } catch (error) {
      console.error("[STT] Query error:", error);
      const errorMsg = error instanceof Error ? error.message : "Failed to process query";
      Alert.alert("Query Error", errorMsg);
    } finally {
      // CRITICAL: Always reset voice processing state, even on timeout/error
      // This prevents "Processing..." from getting stuck
      setIsVoiceProcessing(false);
    }
  }, [tts]);

  const startListening = useCallback(async () => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);

    if (Platform.OS === "web") {
      // Use STT service for Web Speech API
      const success = sttService.startListening(
        (text, isFinal) => {
          setTranscript(text);
          if (isFinal && text.trim()) {
            setIsListening(false);
            processQuery(text.trim());
          }
        },
        (error) => {
          Alert.alert("Speech Recognition Error", error);
          setIsListening(false);
        }
      );

      if (success) {
        setIsListening(true);
        setTranscript("");
      }
    } else {
      // Use expo-av for native recording
      const success = await sttService.startRecordingNative();
      if (success) {
        setIsListening(true);
        setTranscript("Recording...");
      } else {
        Alert.alert("Recording Error", "Failed to start audio recording");
      }
    }
  }, [sttService, processQuery]);

  const stopListening = useCallback(async () => {
    if (Platform.OS === "web") {
      sttService.stopListening();
      setIsListening(false);
    } else {
      // Stop recording and transcribe
      setIsVoiceProcessing(true);
      try {
        const result = await sttService.stopRecordingNative();
        
        if (result.error) {
          Alert.alert("Transcription Error", result.error);
        } else if (result.text && result.text.trim()) {
          // Log exact STT transcription result
          console.log("[STT] Transcribed text =", result.text);
          
          // Check for placeholder text from backend
          const placeholderPatterns = [
            "placeholder",
            "not configured",
            "whisper",
            "transcription not available"
          ];
          const isPlaceholder = placeholderPatterns.some(pattern => 
            result.text.toLowerCase().includes(pattern)
          );
          
          if (isPlaceholder || !result.text.trim()) {
            Alert.alert(
              "STT not configured",
              "Backend /stt/transcribe returns placeholder. Use web STT or integrate Whisper."
            );
          } else {
            setTranscript(result.text);
            await processQuery(result.text);
            // processQuery will reset isVoiceProcessing in its finally block
          }
        } else {
          // FIX: Handle empty/placeholder text - still reset state and show alert
          // Voice got stuck on "Processing..." because empty text didn't reset state
          // Error message from STTService is already helpful, use it directly
          const errorMsg = result.error || "No speech detected. Please try again.";
          Alert.alert("Transcription", errorMsg);
        }
      } catch (error) {
        console.error("[STT] stopListening error:", error);
        Alert.alert("Recording Error", "Failed to process recording");
      } finally {
        // FIX: Always reset voice processing state, even on errors/timeouts
        // Voice got stuck on "Processing..." because state wasn't reset in all error paths
        setIsVoiceProcessing(false);
        setIsListening(false);
      }
    }
  }, [sttService, processQuery]);

  // simple command: "scan text" → OCR mode
  useEffect(() => {
    const t = transcript.toLowerCase();
    if (!t) return;
    if (t.includes("scan text")) setMode("ocr");
  }, [transcript, mode]);

  // --------- auto vision scan ----------

  // Map risk_level string to RiskLevel enum
  const mapRiskLevel = (riskLevelStr: string | undefined): RiskLevel => {
    if (!riskLevelStr) return RiskLevel.MEDIUM;
    const upper = String(riskLevelStr).toUpperCase();
    switch (upper) {
      case "CLEAR":
        return RiskLevel.CLEAR;
      case "LOW":
        return RiskLevel.LOW;
      case "MEDIUM":
        return RiskLevel.MEDIUM;
      case "HIGH":
        return RiskLevel.HIGH;
      case "CRITICAL":
        return RiskLevel.CRITICAL;
      default:
        return RiskLevel.MEDIUM;
    }
  };

  // Capture photo and send to vision/tts endpoint
  // REGRESSION FIX: Auto-scan broke because network calls could hang indefinitely
  // Solution: Add timeout using AbortController, ensure loop never gets stuck
  // Auto-scan is NOT gated by voice state (isVoiceProcessing) - they run independently
  const captureAndProcess = useCallback(async () => {
    // Only gate by request-in-flight flag and camera readiness - NOT by voice state
    if (isRequestInFlight.current || !cameraRef.current) {
      console.log("[Auto Scan] Skipping - request in flight or camera not ready");
      return;
    }

    isRequestInFlight.current = true;
    let timeoutId: NodeJS.Timeout | null = null;

    try {
      // FIX: Add hard timeout to takePictureAsync to prevent scan loop from freezing
      // Auto-scan only ran once because takePictureAsync could hang, blocking the loop
      const photoPromise = cameraRef.current.takePictureAsync({
        quality: 0.7,
        base64: false,
      });
      const timeoutPromise = new Promise<never>((_, reject) => 
        setTimeout(() => reject(new Error("takePictureAsync timeout after 7s")), 7000)
      );
      
      const photo = await Promise.race([photoPromise, timeoutPromise]);

      if (!photo?.uri) {
        console.log("[Auto Scan] Failed to capture photo");
        return; // finally block will reset flag
      }

      console.log("[Auto Scan] Photo captured:", photo.uri);

      const formData = new FormData();
      formData.append(
        "file",
        {
          uri: photo.uri,
          type: "image/jpeg",
          name: "photo.jpg",
        } as any
      );

      const url = `${API_BASE}/vision/tts`;
      console.log("[Auto Scan] Fetching URL:", url);

      // Add timeout to prevent auto-scan from hanging on network issues
      // This restores reliable continuous scanning even when backend is slow/unreachable
      const controller = new AbortController();
      timeoutId = setTimeout(() => {
        controller.abort();
        console.log(`[Auto Scan] Request timed out after ${AUTO_SCAN_TIMEOUT_MS}ms, continuing to next scan cycle`);
      }, AUTO_SCAN_TIMEOUT_MS);

      let response: Response;
      try {
        response = await fetch(url, {
          method: "POST",
          body: formData,
          signal: controller.signal,
        });
      } catch (fetchError: any) {
        const errorMessage = fetchError instanceof Error ? fetchError.message : String(fetchError);
        console.log("[Auto Scan] Fetch error:", errorMessage);
        
        // Don't show alert on timeout - just log and continue scanning
        // This prevents UI spam and keeps auto-scan running
        if (fetchError.name !== 'AbortError') {
          // Only alert on non-timeout errors (e.g., network unreachable)
          Alert.alert("Auto Scan Error", `Network error: ${errorMessage}`);
        }
        return; // Exit early, but ensure finally block runs to reset flag
      }

      if (!response.ok) {
        const errorText = await response.text();
        console.log(`[Auto Scan] API error ${response.status}:`, errorText);
        return;
      }

      const data = await response.json();
      console.log("[Auto Scan] vision/tts response:", data);

      // Determine message to speak
      let messageToSpeak: string;

      if (
        data?.spoken_message &&
        typeof data.spoken_message === "string" &&
        data.spoken_message.trim()
      ) {
        messageToSpeak = data.spoken_message.trim();
      } else if (
        Array.isArray(data?.guidance_messages) &&
        data.guidance_messages.length > 0 &&
        typeof data.guidance_messages[0]?.message === "string" &&
        data.guidance_messages[0].message.trim()
      ) {
        messageToSpeak = data.guidance_messages[0].message.trim();
      } else {
        messageToSpeak = "No hazards detected";
      }

      const riskLevel = data?.guidance_messages?.[0]?.risk_level
        ? mapRiskLevel(data.guidance_messages[0].risk_level)
        : RiskLevel.MEDIUM;

      // Filter out placeholder/empty messages and deduplicate
      const now = Date.now();
      const timeSinceLastSpoken = now - lastSpokenTime.current;
      const isPlaceholder = 
        !messageToSpeak || 
        messageToSpeak === "Test audio works" || 
        messageToSpeak === "No hazards detected";
      const isDuplicate = messageToSpeak === lastSpokenMessage.current && timeSinceLastSpoken < 5000;

      if (isPlaceholder || isDuplicate) {
        console.log(`[Auto Scan] Skipping speech - ${isPlaceholder ? 'placeholder/empty message' : 'duplicate within 5s'}: "${messageToSpeak}"`);
        return; // Skip speaking but continue scan loop
      }

      // FIX: Removed tts.stop() - it was causing silence. Let force=true handle overlap
      // Auto-scan only ran once because stopping TTS before every speak caused silent failures
      // Speak (force=true) - TTS announcements restored
      await tts.speak(messageToSpeak, riskLevel, true);
      
      // Update deduplication refs
      lastSpokenMessage.current = messageToSpeak;
      lastSpokenTime.current = now;
    } catch (error) {
      console.log("[Auto Scan] Error:", error);
    } finally {
      // CRITICAL: Always reset flag and clear timeout, even on timeout/error
      // This ensures auto-scan loop continues reliably
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
      isRequestInFlight.current = false;
    }
  }, [tts]);

  // Auto scan interval effect
  useEffect(() => {
    if (isAutoScanning && mode === "voice") {
      console.log(`[Auto Scan] Starting interval loop (${AUTO_SCAN_INTERVAL_MS}ms interval)`);
      scanIntervalRef.current = setInterval(() => {
        captureAndProcess();
      }, AUTO_SCAN_INTERVAL_MS) as unknown as number;
    } else {
      if (scanIntervalRef.current) {
        console.log("[Auto Scan] Stopping interval loop");
        clearInterval(scanIntervalRef.current);
        scanIntervalRef.current = null;
      }
    }

    return () => {
      if (scanIntervalRef.current) {
        clearInterval(scanIntervalRef.current);
        scanIntervalRef.current = null;
      }
    };
  }, [isAutoScanning, mode, captureAndProcess]);

  // Stop auto scan when leaving voice mode
  useEffect(() => {
    if (mode !== "voice" && isAutoScanning) setIsAutoScanning(false);
  }, [mode, isAutoScanning]);

  // --------- permission gate ----------
  if (!perm) return <View style={{ flex: 1, backgroundColor: "#1B263B" }} />;

  if (!perm.granted) {
    return (
      <SafeAreaView style={styles.screen} edges={["top"]}>
        <View style={[styles.content, { width: contentWidth }]}>
          <HomeHeader
            greeting="Hi!"
            appTitle="WalkBuddy"
            onPressProfile={() => router.push("/account")}
            showDivider
            showLocation
          />

          <View style={styles.centerCard}>
            <Text style={styles.centerText}>
              Camera access is required for Voice Assist.
            </Text>

            <Pressable style={styles.primaryBtn} onPress={requestPermission}>
              <Text style={styles.primaryBtnText}>Grant Permission</Text>
            </Pressable>
          </View>

          <Footer />
        </View>
      </SafeAreaView>
    );
  }

  // --------- UI ----------
  return (
    <SafeAreaView style={styles.screen} edges={["top"]}>
      <View style={[styles.content, { width: contentWidth }]}>
        <HomeHeader
          greeting="Hi!"
          appTitle="WalkBuddy"
          onPressProfile={() => router.push("/account")}
          showDivider
          showLocation
        />

        <View style={styles.modeTitleRow}>
          <Text style={styles.modeTitle}>
            {mode === "ocr"
              ? "SCAN TEXT"
              : mode === "voice"
              ? "VOICE ASSIST"
              : mode === "vision"
              ? "VISION ASSIST"
              : "ASSISTANT"}
          </Text>
        </View>

        <View style={[styles.previewBox, { height: previewHeight }]}>
          {mode === "voice" ? (
            <CameraView
              ref={cameraRef}
              style={StyleSheet.absoluteFill}
              facing="back"
            />
          ) : mode === "vision" || mode === "ocr" ? (
            <ModelWebView url={url} loading={loading} />
          ) : (
            <View style={{ flex: 1, backgroundColor: tokens.bg }} />
          )}
        </View>

        <View style={styles.modeBar}>
          <ModeBtn
            label="Vision"
            active={mode === "vision"}
            onPress={() => {
              Haptics.selectionAsync();
              setMode("vision");
            }}
          />

      <View style={styles.modeBar}>
        <ModeBtn
          label="Vision"
          active={mode === "vision"}
          onPress={() => {
            Haptics.selectionAsync();
            setMode("vision");
          }}
        />
        <ModeBtn
          label="Voice Assist"
          active={mode === "voice"}
          onPress={() => {
            Haptics.selectionAsync();
            if (isListening) stopListening();
            setMode("voice");
          }}
        />
        <ModeBtn
          label="Scan Text"
          active={mode === "ocr"}
          onPress={() => {
            Haptics.selectionAsync();
            setMode("ocr");
          }}
        />
      </View>

      {mode === "voice" && (
        <>
          <View style={styles.voiceRow}>
            <Pressable
              onPress={isListening ? stopListening : startListening}
              style={[styles.micBtn, isListening && styles.micBtnActive]}
              disabled={!sttAvailable && Platform.OS !== "web"}
            >
              <MaterialIcons
                name={isListening ? "mic" : "mic-none"}
                size={28}
                color={isListening ? "#1B263B" : GOLD}
              />
            </Pressable>

            <View style={styles.voiceTextWrap}>
              <Text style={styles.voiceHint}>
                {isVoiceProcessing
                  ? "Processing..."
                  : sttAvailable || Platform.OS === "web"
                  ? isListening
                    ? Platform.OS === "web"
                      ? "Listening… speak now"
                      : "Recording... tap to stop"
                    : "Tap the mic and speak"
                  : "Mic requires native STT (Dev Client)"}
              </Text>
              {!!transcript && !isVoiceProcessing && (
                <Text style={styles.voiceTranscript}>{transcript}</Text>
              )}
            </View>
          </View>

          <View style={styles.testTTSContainer}>
            <Pressable
              style={styles.testTTSButton}
              onPress={async () => {
                Alert.alert("TTS Test", "Button pressed - speaking test message");
                await tts.speak("Test audio works", RiskLevel.LOW, true);
              }}
            >
              <Text style={styles.testTTSButtonText}>Test TTS</Text>
            </Pressable>

            <Pressable
              style={[
                styles.testTTSButton,
                isAutoScanning && styles.autoScanButtonActive,
              ]}
              onPress={() => {
                if (!isAutoScanning) {
                  Alert.alert("Auto Scan", `API_BASE = ${API_BASE}`);
                }
                setIsAutoScanning(!isAutoScanning);
                Haptics.selectionAsync();
              }}
            >
              <Text style={styles.testTTSButtonText}>
                {isAutoScanning ? "Stop Auto Scan" : "Start Auto Scan"}
              </Text>
            </Pressable>
          </View>
        </>
      )}
    </View>
  );
}

function ModeBtn({
  label,
  active,
  onPress,
}: {
  label: string;
  active: boolean;
  onPress: () => void;
}) {
  return (
    <Pressable
      onPress={onPress}
      style={[styles.modeBtn, active && styles.modeBtnActive]}
    >
      <Text style={[styles.modeBtnText, active && styles.modeBtnTextActive]}>
        {label}
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: tokens.bg,
    alignItems: "center",
  },

  content: {
    flex: 1,
    paddingHorizontal: 12,
    paddingTop: 8,
    paddingBottom: 0,
  },

  modeTitleRow: {
    paddingHorizontal: 14,
    paddingTop: 2,
    paddingBottom: 10,
  },
  modeTitle: {
    color: tokens.gold,
    fontSize: 18,
    fontWeight: "900",
    letterSpacing: 0.6,
  },

  previewBox: {
    width: "100%",
    borderRadius: 14,
    overflow: "hidden",
    backgroundColor: tokens.card,
    borderWidth: 2,
    borderColor: tokens.gold,
  },

  modeBar: {
    flexDirection: "row",
    gap: 10,
    justifyContent: "space-around",
    paddingHorizontal: 12,
    paddingTop: 12,
    paddingBottom: 8,
  },

  modeBtn: {
    flex: 1,
    borderWidth: 2,
    borderColor: tokens.gold,
    borderRadius: 12,
    paddingVertical: 10,
    alignItems: "center",
    backgroundColor: tokens.card,
  },
  modeBtnActive: { backgroundColor: tokens.gold },
  modeBtnText: { color: tokens.gold, fontWeight: "800" },
  modeBtnTextActive: { color: tokens.bg },

  voiceRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    paddingHorizontal: 14,
    paddingVertical: 12,
  },

  micBtn: {
    width: 56,
    height: 56,
    borderRadius: 28,
    borderWidth: 2,
    borderColor: tokens.gold,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: tokens.card,
  },
  micBtnActive: { backgroundColor: tokens.gold },

  voiceTextWrap: { flex: 1 },
  voiceHint: { color: tokens.gold, fontWeight: "800" },
  voiceTranscript: { color: tokens.text, marginTop: 6 },

  centerCard: {
    flex: 1,
    borderWidth: 2,
    borderColor: tokens.gold,
    borderRadius: 14,
    backgroundColor: tokens.card,
    padding: 16,
    marginTop: 14,
    justifyContent: "center",
    alignItems: "center",
    gap: 12,
  },
  centerText: { color: tokens.text, fontWeight: "700", textAlign: "center" },

  primaryBtn: {
    backgroundColor: tokens.gold,
    paddingVertical: 12,
    paddingHorizontal: 18,
    borderRadius: 12,
  },
  primaryBtnText: { color: "#1B263B", fontWeight: "800" },
  testTTSContainer: {
    paddingHorizontal: 16,
    paddingBottom: 12,
    gap: 10,
  },
  testTTSButton: {
    backgroundColor: GOLD,
    paddingVertical: 12,
    paddingHorizontal: 18,
    borderRadius: 12,
    alignItems: "center",
  },
  testTTSButtonText: { color: "#1B263B", fontWeight: "800" },
  autoScanButtonActive: {
    backgroundColor: "#ff6b6b",
  },
});
