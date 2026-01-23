// app/camera.tsx
import { MaterialIcons } from "@expo/vector-icons";
import { CameraView, useCameraPermissions } from "expo-camera";
import * as Haptics from "expo-haptics";
import * as Speech from "expo-speech";
import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  Alert,
  Dimensions,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  View,
  ActivityIndicator,
  ScrollView,
  useWindowDimensions,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useRouter, useLocalSearchParams } from "expo-router";

import { askTwoBrain, detectObject } from "../src/api/client";
import HomeHeader from "./HomeHeader";
import Footer from "./Footer";

const tokens = {
  bg: "#0D1B2A",
  card: "#111",
  gold: "#FCA311",
  text: "#E0E1DD",
};

const GOLD = tokens.gold; // mapping for legacy code

type Mode = "idle" | "vision" | "voice" | "ocr";

export default function CameraAssistScreen() {
  const router = useRouter();
  const { width, height } = useWindowDimensions();

  // Layout calculations
  const contentWidth = useMemo(() => {
    const padding = 24;
    const max = 720;
    return Math.min(max, Math.max(320, width - padding * 2));
  }, [width]);

  const previewHeight = useMemo(() => {
    const h = Math.round(height * 0.52);
    return Math.max(260, Math.min(520, h));
  }, [height]);

  // Mode state
  const [mode, setMode] = useState<Mode>("vision");
  const { mode: modeParam } = useLocalSearchParams<{ mode?: Mode }>();

  // Deep link param handling
  useEffect(() => {
    if (modeParam === "vision" || modeParam === "voice" || modeParam === "ocr") {
      setMode(modeParam);
    }
  }, [modeParam]);

  // Camera permissions
  const [perm, requestPermission] = useCameraPermissions();
  const cameraRef = useRef<CameraView>(null);

  // Logic State
  const [processing, setProcessing] = useState(false);
  const [lastSpoken, setLastSpoken] = useState<string>("");
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const recognitionRef = useRef<any>(null);

  // --- TTS Helper ---
  const speak = useCallback((msg: string) => {
    Speech.stop();
    Speech.speak(msg, { rate: 1.0 });
  }, []);

  // --- API Functions ---
  const processFrame = async (blob: Blob) => {
    try {
      if (mode === "vision") {
        const res = await detectObject(blob);
        const best = res.events
          .filter(e => e.confidence > 0.5)
          .sort((a, b) => b.confidence - a.confidence)[0];

        if (best) {
          const msg = `${best.label} ${best.direction}`;
          if (msg !== lastSpoken) {
            speak(msg);
            setLastSpoken(msg);
            Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
          }
        }
      }
    } catch (e) {
      console.error("Vision error:", e);
    }
  };

  const processQuery = async (blob: Blob, question: string) => {
    try {
      setProcessing(true);
      speak("Thinking...");
      const res = await askTwoBrain(blob, question);
      setProcessing(false);

      if (!res.safe) {
        Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error);
        speak(res.answer || "Unsafe to proceed.");
      } else {
        Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
        speak(res.answer || "I see nothing notable.");
      }
    } catch (e) {
      console.error("TwoBrain error:", e);
      setProcessing(false);
      speak("Sorry, I had trouble thinking.");
    }
  };

  // --- Vision Loop ---
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (mode === "vision" && !processing) {
      interval = setInterval(async () => {
        if (cameraRef.current) {
          try {
            const photo = await cameraRef.current.takePictureAsync({ quality: 0.5, skipProcessing: true });
            if (photo?.uri) {
              const response = await fetch(photo.uri);
              const blob = await response.blob();
              await processFrame(blob);
            }
          } catch (err) {
            console.log("Vision loop err", err);
          }
        }
      }, 2000);
    }
    return () => clearInterval(interval);
  }, [mode, processing, lastSpoken]);

  // --- Voice Logic ---
  const startListening = useCallback(() => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    setTranscript("");

    if (Platform.OS === "web") {
      const W = globalThis as any;
      const SR = W.SpeechRecognition || W.webkitSpeechRecognition;
      if (!SR) return alert("No Speech API");

      const rec = new SR();
      recognitionRef.current = rec;
      rec.lang = "en-US";
      rec.onresult = (e: any) => {
        const t = e.results[0][0].transcript;
        setTranscript(t);
      };
      rec.onend = () => {
        setIsListening(false);
        if (transcript) handleSendQuery(transcript);
      };
      rec.start();
      setIsListening(true);
    } else {
      Alert.alert("Native STT", "Tap 'Scan Text' just to simulate a query for this demo.");
      setTranscript("What is ahead?");
      setIsListening(true);
      setTimeout(() => {
        setIsListening(false);
        handleSendQuery("What is in front of me?");
      }, 1500);
    }
  }, []);

  const handleSendQuery = async (text: string) => {
    if (!text) return;
    if (cameraRef.current) {
      const photo = await cameraRef.current.takePictureAsync({ quality: 0.5 });
      if (photo?.uri) {
        const response = await fetch(photo.uri);
        const blob = await response.blob();
        await processQuery(blob, text);
      }
    }
  };

  const stopListening = () => {
    if (recognitionRef.current) recognitionRef.current.stop();
    setIsListening(false);
    if (transcript) handleSendQuery(transcript);
  };

  // --- Render ---

  if (!perm) {
    return <View style={{ flex: 1, backgroundColor: tokens.bg }} />;
  }

  if (!perm.granted) {
    return (
      <SafeAreaView style={styles.screen} edges={["top"]}>
        <View style={[styles.content, { width: contentWidth }]}>
          <HomeHeader
            greeting="Hi!"
            appTitle="WalkBuddy"
            onPressProfile={() => router.push("/profile")}
            showDivider
            showLocation
          />
          <View style={styles.centerCard}>
            <Text style={styles.centerText}>Camera access is required.</Text>
            <Pressable style={styles.primaryBtn} onPress={requestPermission}>
              <Text style={styles.primaryBtnText}>Grant Permission</Text>
            </Pressable>
          </View>
          <Footer />
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.screen} edges={["top"]}>
      <View style={[styles.content, { width: contentWidth }]}>
        <HomeHeader
          greeting="Hi!"
          appTitle="WalkBuddy"
          onPressProfile={() => router.push("/profile")}
          showDivider
          showLocation
        />

        <ScrollView
          style={styles.scroll}
          contentContainerStyle={styles.scrollContent}
          showsVerticalScrollIndicator={false}
        >
          <View style={styles.modeTitleRow}>
            <Text style={styles.modeTitle}>
              {mode === "vision" ? "VISION (Two-Brain)" : "VOICE ASSIST"}
            </Text>
            {processing && <ActivityIndicator size="small" color={GOLD} />}
          </View>

          <View style={[styles.previewBox, { height: previewHeight }]}>
            <CameraView ref={cameraRef} style={StyleSheet.absoluteFill} facing="back" />
            <View style={styles.overlay}>
              <Text style={styles.overlayText}>{processing ? "Thinking..." : lastSpoken}</Text>
            </View>
          </View>

          <View style={styles.modeBar}>
            <ModeBtn label="Vision" active={mode === "vision"} onPress={() => { setMode("vision"); Haptics.selectionAsync(); }} />
            <ModeBtn label="Voice Assist" active={mode === "voice"} onPress={() => { setMode("voice"); Haptics.selectionAsync(); }} />
          </View>

          {mode === "voice" && (
            <View style={styles.voiceRow}>
              <Pressable
                onPress={isListening ? stopListening : startListening}
                style={[styles.micBtn, isListening && styles.micBtnActive]}
              >
                <MaterialIcons
                  name={isListening ? "mic" : "mic-none"}
                  size={28}
                  color={isListening ? tokens.bg : tokens.gold}
                />
              </Pressable>

              <View style={styles.voiceTextWrap}>
                <Text style={styles.voiceHint}>
                  {isListening ? "Listening…" : "Tap the mic and speak"}
                </Text>
                {!!transcript && (
                  <Text style={styles.voiceTranscript}>{transcript}</Text>
                )}
              </View>
            </View>
          )}
        </ScrollView>

        <Footer />
      </View>
    </SafeAreaView>
  );
}

function ModeBtn({ label, active, onPress }: any) {
  return (
    <Pressable onPress={onPress} style={[styles.modeBtn, active && styles.modeBtnActive]}>
      <Text style={[styles.modeBtnText, active && styles.modeBtnTextActive]}>{label}</Text>
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
  },
  scroll: {
    flex: 1,
  },
  scrollContent: {
    paddingBottom: 16,
  },
  modeTitleRow: {
    paddingHorizontal: 14,
    paddingTop: 2,
    paddingBottom: 10,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center'
  },
  modeTitle: {
    color: tokens.gold,
    fontSize: 18,
    fontWeight: "900",
  },
  previewBox: {
    width: "100%",
    borderRadius: 14,
    overflow: "hidden",
    backgroundColor: "#000",
    borderWidth: 2,
    borderColor: tokens.gold,
    position: 'relative'
  },
  overlay: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    backgroundColor: 'rgba(0,0,0,0.5)',
    padding: 10
  },
  overlayText: { color: 'white', textAlign: 'center', fontSize: 16 },
  modeBar: {
    flexDirection: "row",
    gap: 10,
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
  primaryBtnText: { color: tokens.bg, fontWeight: "900" },
});

