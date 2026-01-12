// HomeHeader.tsx
import React, { useMemo } from "react";
import { View, Text, Pressable, StyleSheet, Switch } from "react-native";
import Icon from "react-native-vector-icons/FontAwesome";
import { useSegments } from "expo-router";
import { useCurrentLocation } from "./lib/locationSaver";

type Props = {
  greeting?: string;        // Home only (future profile will supply this)
  appTitle?: string;        // Branding in the centre
  onPressProfile?: () => void;

  showDivider?: boolean;
  showLocation?: boolean;

  // Fallback only (if provider empty)
  locationValue?: string;
};

function titleCaseFromSegment(seg: string) {
  const cleaned = (seg ?? "").replace(/[-_]/g, " ").trim();
  if (!cleaned) return "";
  return cleaned
    .split(" ")
    .filter(Boolean)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

function getRouteNameFromSegments(segments: string[]) {
  const usable = segments.filter((s) => !s.startsWith("(") && s.length > 0);
  if (usable.length === 0) return "";
  const last = usable[usable.length - 1];
  if (last.toLowerCase() === "index") return "Home";
  return titleCaseFromSegment(last);
}

function isHomeBySegments(segments: string[]) {
  const usable = segments.filter((s) => !s.startsWith("(") && s.length > 0);
  if (usable.length === 0) return true;
  const last = (usable[usable.length - 1] ?? "").toLowerCase();
  return last === "home" || last === "index";
}

export default function HomeHeader({
  greeting = "Hi!",
  appTitle = "WalkBuddy",
  onPressProfile,

  showDivider = true,
  showLocation = true,

  locationValue = "",
}: Props) {
  const segments = useSegments();
  const {
    currentLocation,
    destination,
    preferDestinationView,
    setPreferDestinationView,
  } = useCurrentLocation();

  const derived = useMemo(() => {
    const onHome = isHomeBySegments(segments);

    const routeName = getRouteNameFromSegments(segments);
    const leftText = onHome ? greeting : `${routeName || "Page"} Page`;

    const hasDestination = !!destination && destination.trim().length > 0;
    const showingDestination = hasDestination && preferDestinationView;

    const label = showingDestination ? "DESTINATION" : "LOCATION";
    const value =
      (showingDestination ? destination : currentLocation) || locationValue;

    return {
      leftText,
      hasDestination,
      label,
      value,
      switchValue: hasDestination ? preferDestinationView : false,
    };
  }, [segments, greeting, currentLocation, destination, preferDestinationView, locationValue]);

  return (
    <View style={styles.wrap}>
      <View style={styles.headerRow}>
        <Text style={styles.greeting} numberOfLines={1}>
          {derived.leftText}
        </Text>

        <Text style={styles.title} numberOfLines={1}>
          {appTitle}
        </Text>

        <Pressable
          onPress={onPressProfile}
          disabled={!onPressProfile}
          accessibilityLabel="Account"
          hitSlop={10}
          style={styles.profileBtn}
        >
          <Icon name="user-circle" size={26} color={tokens.gold} />
        </Pressable>
      </View>

      {showDivider && <View style={styles.topDivider} />}

      {showLocation && (
        <View style={styles.locationWrap}>
          <Text style={styles.locationLabel}>{derived.label}</Text>

          <View style={styles.locationOuterCard}>
            <View style={styles.locationInnerRow}>
              <Text style={styles.locationValue} numberOfLines={1}>
                {derived.value}
              </Text>

              <Switch
                disabled={!derived.hasDestination}
                value={derived.switchValue}
                onValueChange={(v) => {
                  if (!derived.hasDestination) return;
                  setPreferDestinationView(v);
                }}
                trackColor={{ false: "#23384d", true: "#2d4b66" }}
                thumbColor={derived.switchValue ? tokens.gold : "#9aa8b6"}
              />
            </View>
          </View>
        </View>
      )}
    </View>
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
  wrap: {
    width: "100%",
  },

  headerRow: {
    width: "100%",
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 12,
  },

  greeting: {
    color: tokens.text,
    fontSize: 14,
    fontWeight: "600",
    flexShrink: 1,
  },

  title: {
    color: tokens.text,
    fontSize: 22,
    fontWeight: "800",
    flexShrink: 1,
    marginHorizontal: 12,
  },

  profileBtn: {
    paddingLeft: 10,
  },

  topDivider: {
    borderBottomWidth: 1,
    borderBottomColor: tokens.divider,
    marginBottom: 12,
  },

  locationWrap: {
    width: "100%",
    marginBottom: 16,
  },

  locationLabel: {
    color: tokens.muted,
    fontSize: 12,
    fontWeight: "800",
    letterSpacing: 0.6,
    marginBottom: 8,
  },

  locationOuterCard: {
    width: "100%",
    backgroundColor: tokens.tile,
    borderWidth: 2,
    borderColor: tokens.gold,
    borderRadius: 16,
    padding: 12,
  },

  locationInnerRow: {
    width: "100%",
    backgroundColor: "#0a121a",
    borderWidth: 2,
    borderColor: tokens.gold,
    borderRadius: 14,
    paddingVertical: 14,
    paddingHorizontal: 14,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 12,
  },

  locationValue: {
    color: tokens.text,
    fontSize: 14,
    fontWeight: "800",
    letterSpacing: 0.4,
    flexShrink: 1,
  },
});
  