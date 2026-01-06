// home.tsx (HomePage)
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "expo-router";
import {
  StyleSheet,
  Text,
  View,
  Pressable,
  Switch,
  useWindowDimensions,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import Icon from "react-native-vector-icons/FontAwesome";
import HomeHeader from "./HomeHeader";
import Footer from "./Footer";
import ModelWebView from "../src/components/ModelWebView";
import { API_BASE } from "../src/config";

export default function HomePage() {
  const router = useRouter();
  const { width } = useWindowDimensions();

  const [visionEnabled, setVisionEnabled] = useState(true);

  // This controls whether the object-detection preview is mounted in the Home window.
  const [visionPreviewOn, setVisionPreviewOn] = useState(false);

  // Mirror the pattern from app/camera.tsx for cache-busting and a small warmup loading state.
  const [loading, setLoading] = useState(false);
  const [rev, setRev] = useState(0);

  const contentWidth = useMemo(() => {
    const padding = 24;
    const max = 720;
    return Math.min(max, Math.max(320, width - padding * 2));
  }, [width]);

  const goToAccount = () => router.push("/account");
  const goToNavigate = () => router.push("/navigate");
  const goToSavedPlaces = () => router.push("/places");
  const goToCameraScreen = () => router.push("/camera");

  // If Vision Assist is turned off, force preview off.
  useEffect(() => {
    if (!visionEnabled) {
      setVisionPreviewOn(false);
      setLoading(false);
    }
  }, [visionEnabled]);

  // When preview is turned on, refresh the webview and show a short loading warmup.
  useEffect(() => {
    if (!visionPreviewOn) {
      setLoading(false);
      return;
    }

    setLoading(true);
    setRev((x) => x + 1);

    const t = setTimeout(() => setLoading(false), 800);
    return () => clearTimeout(t);
  }, [visionPreviewOn]);

  const visionUrl = useMemo(() => {
    return `${API_BASE}/vision/?v=${rev}`;
  }, [rev]);

  const toggleVisionPreview = () => {
    if (!visionEnabled) return;
    setVisionPreviewOn((prev) => !prev);
  };

  const visionHintText = useMemo(() => {
    if (!visionEnabled) return "Vision disabled";
    return visionPreviewOn ? "Tap to turn preview off" : "Tap to turn preview on";
  }, [visionEnabled, visionPreviewOn]);

  return (
    <SafeAreaView style={styles.screen}>
      <View style={[styles.content, { width: contentWidth }]}>
        <HomeHeader
          greeting="Hi George!"
          title="WalkBuddy"
          onPressProfile={goToAccount}
          showDivider={true}
          showLocation={true}
          locationLabel="LOCATION"
          locationValue="1 HERE ST THERE"
          locationEnabled={visionEnabled}
          onToggleLocation={setVisionEnabled}
        />

        <View style={styles.mainArea}>
          <Pressable style={styles.searchButton} onPress={goToNavigate}>
            <Text style={styles.searchText}>SEARCH</Text>
          </Pressable>

          <View style={styles.grid}>
            <ActionTile icon="microphone" label="VOICE ASSIST" onPress={goToCameraScreen} />
            <ActionTile icon="map-marker" label="PLACES" onPress={goToSavedPlaces} />
            <ActionTile icon="volume-up" label="SCREEN READER" onPress={goToCameraScreen} />
            <ActionTile icon="file-text" label="TEXT READER" onPress={goToCameraScreen} />
          </View>

          <View style={styles.visionRow}>
            <Text style={styles.visionTitle}>VISION ASSIST</Text>

            <View style={styles.visionToggle}>
              <Text style={styles.visionToggleText}>
                {visionEnabled ? "On" : "Off"}
              </Text>
              <Switch
                value={visionEnabled}
                onValueChange={setVisionEnabled}
                trackColor={{ false: "#23384d", true: "#2d4b66" }}
                thumbColor={visionEnabled ? tokens.gold : "#9aa8b6"}
              />
            </View>
          </View>

          {/* Press this card to toggle the object detection pipeline preview on/off */}
          <Pressable
            style={[
              styles.visionCard,
              !visionEnabled ? styles.visionCardDisabled : null,
            ]}
            onPress={toggleVisionPreview}
          >
            <View style={styles.visionInner}>
              {visionEnabled && visionPreviewOn ? (
                <ModelWebView url={visionUrl} loading={loading} />
              ) : (
                <View style={styles.previewPlaceholder}>
                  <Icon
                    name={visionEnabled ? "eye" : "ban"}
                    size={28}
                    color={tokens.gold}
                  />
                  <Text style={styles.previewText}>VISION PREVIEW</Text>
                  <Text style={styles.previewSubtext}>{visionHintText}</Text>
                </View>
              )}
            </View>
          </Pressable>
        </View>

        <Footer />
      </View>
    </SafeAreaView>
  );
}

function ActionTile({
  icon,
  label,
  onPress,
}: {
  icon: string;
  label: string;
  onPress: () => void;
}) {
  return (
    <Pressable style={styles.tile} onPress={onPress}>
      <Icon name={icon} size={22} color={tokens.gold} />
      <Text style={styles.tileText}>{label}</Text>
    </Pressable>
  );
}

const tokens = {
  bg: "#071a2a",
  tile: "#0b0f14",
  text: "#e8eef6",
  muted: "#b8c6d4",
  gold: "#f2a900",
  divider: "#f2a900",
};

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

  mainArea: {
    flex: 1,
    width: "100%",
    justifyContent: "flex-start",
    paddingTop: 8,
  },

  searchButton: {
    width: "100%",
    backgroundColor: tokens.tile,
    borderWidth: 2,
    borderColor: tokens.gold,
    borderRadius: 14,
    paddingVertical: 16,
    alignItems: "center",
    marginBottom: 18,
  },

  searchText: {
    color: tokens.text,
    fontSize: 16,
    fontWeight: "800",
    letterSpacing: 0.5,
  },

  grid: {
    width: "100%",
    flexDirection: "row",
    flexWrap: "wrap",
    justifyContent: "space-between",
    gap: 18,
    marginBottom: 20,
  },

  tile: {
    width: "48%",
    backgroundColor: tokens.tile,
    borderWidth: 2,
    borderColor: tokens.gold,
    borderRadius: 14,
    paddingVertical: 26,
    alignItems: "center",
    justifyContent: "center",
    gap: 10,
  },

  tileText: {
    color: tokens.text,
    fontSize: 12,
    fontWeight: "800",
    textAlign: "center",
  },

  visionRow: {
    width: "100%",
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 10,
  },

  visionTitle: {
    color: tokens.text,
    fontSize: 14,
    fontWeight: "900",
    letterSpacing: 0.4,
  },

  visionToggle: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
  },

  visionToggleText: {
    color: tokens.muted,
    fontSize: 12,
    fontWeight: "800",
  },

  visionCard: {
    width: "100%",
    flex: 1,
    backgroundColor: tokens.tile,
    borderWidth: 2,
    borderColor: tokens.gold,
    borderRadius: 14,
    padding: 14,
    marginBottom: 6,
  },

  visionCardDisabled: {
    opacity: 0.5,
  },

  visionInner: {
    flex: 1,
    borderWidth: 2,
    borderColor: tokens.gold,
    borderRadius: 12,
    overflow: "hidden",
    backgroundColor: "#0a121a",
  },

  previewPlaceholder: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    paddingHorizontal: 16,
  },

  previewText: {
    color: tokens.text,
    fontSize: 13,
    fontWeight: "900",
    textAlign: "center",
    letterSpacing: 0.6,
  },

  previewSubtext: {
    color: tokens.muted,
    fontSize: 12,
    fontWeight: "700",
    textAlign: "center",
    marginTop: 4,
  },

  bottomDivider: {
    borderBottomWidth: 1,
    borderBottomColor: tokens.divider,
    marginTop: 12,
    marginBottom: 10,
  },

  bottomNav: {
    width: "100%",
    flexDirection: "row",
    justifyContent: "space-around",
    paddingVertical: 10,
  },
});
