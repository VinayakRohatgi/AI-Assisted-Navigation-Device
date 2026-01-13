// app/search.tsx
import React, { useEffect, useMemo, useState } from "react";
import { useLocalSearchParams, useRouter } from "expo-router";
import {
  StyleSheet,
  Text,
  View,
  Pressable,
  TextInput,
  useWindowDimensions,
  Alert,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import Icon from "react-native-vector-icons/FontAwesome";

import HomeHeader from "./HomeHeader";
import Footer from "./Footer";

/*
  NOTE:
  This screen is currently UI-FIRST.
  No real search, geocoding, or navigation handoff is implemented yet.

  Intended future behaviour:
  - User types or receives a destination (from Places, voice, etc.)
  - Destination is validated / resolved (internal or external)
  - Correct navigation engine is selected
  - Destination is passed into internalNavigation / externalNavigation

  For now:
  - Buttons show a temporary notice
  - Layout, spacing, and flow are being validated
*/

const tokens = {
  bg: "#0D1B2A",
  tile: "#111",
  text: "#E0E1DD",
  muted: "#b8c6d4",
  gold: "#FCA311",
};

export default function SearchPage() {
  const router = useRouter();

  const { width, height } = useWindowDimensions();
  const resultFontSize = Math.max(26, Math.min(36, height * 0.045));

  const { presetDestination } = useLocalSearchParams<{
    presetDestination?: string;
  }>();

  const contentWidth = useMemo(() => {
    const padding = 24;
    const max = 720;
    return Math.min(max, Math.max(320, width - padding * 2));
  }, [width]);

  const [query, setQuery] = useState("");

  // Prefill search field when coming from Places
  // Later this will also trigger destination resolution logic
  useEffect(() => {
    if (typeof presetDestination !== "string") return;
    setQuery(presetDestination);
  }, [presetDestination]);

  /*
    TEMPORARY HANDLERS
    These will be replaced once navigation engines are wired.
  */
  const handleNotReady = () => {
    Alert.alert(
      "Not implemented yet",
      "This feature will be updated shortly."
    );
  };

  return (
    <SafeAreaView style={styles.screen} edges={["top"]}>
      <View style={[styles.content, { width: contentWidth }]}>
        <HomeHeader
          appTitle="WalkBuddy"
          onPressProfile={() => router.push("/account" as any)}
          showDivider
          showLocation
        />

        {/* Spacer below header (visual breathing room) */}
        <View style={{ height: 12 }} />
        <View style={{ height: 12 }} />

        <View style={styles.mainArea}>
          <Text style={styles.sectionTitle}>Enter Your Search</Text>

          {/* Search input (UI only – no real search yet) */}
          <View style={styles.searchBar}>
            <Icon name="search" size={18} color={tokens.muted} />
            <TextInput
              value={query}
              onChangeText={setQuery}
              placeholder="Enter a destination"
              placeholderTextColor={tokens.muted}
              style={styles.searchInput}
              autoCapitalize="words"
              autoCorrect={false}
            />
          </View>

          {/* Result display area
              This will later show resolved destinations / options */}
          <View style={styles.resultCard}>
            <Text
              style={[styles.resultTitle, { fontSize: resultFontSize }]}
              numberOfLines={3}
            >
              {query.length > 0 ? query : "LARGE TEXT"}
            </Text>

            <Text style={styles.resultSub} numberOfLines={3}>
              {query.length > 0
                ? "This is the address searched for"
                : "This is the address searched for XYZ"}
            </Text>
          </View>

          {/* Navigation mode buttons
              Currently disabled logically – show notice only */}
          <View style={styles.buttonRow}>
            <Pressable style={styles.modeBtn} onPress={handleNotReady}>
              <Text style={styles.modeBtnText}>INTERIOR</Text>
            </Pressable>

            <Pressable style={styles.modeBtn} onPress={handleNotReady}>
              <Text style={styles.modeBtnText}>MAPS</Text>
            </Pressable>
          </View>

          <View style={{ height: 12 }} />
          <View style={{ height: 12 }} />
        </View>

        <Footer />
      </View>
    </SafeAreaView>
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

  mainArea: {
    flex: 1,
    width: "100%",
    paddingTop: 16,
    paddingHorizontal: 14,
    gap: 18,
  },

  sectionTitle: {
    color: tokens.text,
    fontSize: 16,
    fontWeight: "800",
    marginBottom: 6,
  },

  searchBar: {
    width: "100%",
    height: 56,
    backgroundColor: tokens.tile,
    borderWidth: 2,
    borderColor: tokens.gold,
    borderRadius: 14,
    paddingHorizontal: 14,
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
  },

  searchInput: {
    flex: 1,
    color: tokens.text,
    fontSize: 16,
    fontWeight: "700",
  },

  resultCard: {
    width: "100%",
    backgroundColor: tokens.tile,
    borderWidth: 2,
    borderColor: tokens.gold,
    borderRadius: 18,
    paddingVertical: 26,
    paddingHorizontal: 16,
    alignItems: "center",
    justifyContent: "center",
    gap: 10,

    flexGrow: 1,
    flexBasis: "45%",
    minHeight: 260,
  },

  resultTitle: {
    color: tokens.text,
    fontWeight: "900",
    textAlign: "center",
    letterSpacing: 0.6,
  },

  resultSub: {
    color: tokens.text,
    opacity: 0.75,
    fontSize: 14,
    fontWeight: "700",
    textAlign: "center",
    lineHeight: 20,
  },

  buttonRow: {
    width: "100%",
    flexDirection: "row",
    gap: 12,
  },

  modeBtn: {
    flex: 1,
    backgroundColor: tokens.tile,
    borderWidth: 2,
    borderColor: tokens.gold,
    borderRadius: 14,
    paddingVertical: 18,
    alignItems: "center",
  },

  modeBtnText: {
    color: tokens.text,
    fontSize: 14,
    fontWeight: "900",
    letterSpacing: 0.6,
  },
});
