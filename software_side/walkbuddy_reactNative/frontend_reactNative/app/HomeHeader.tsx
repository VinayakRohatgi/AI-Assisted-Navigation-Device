// HomeHeader.tsx
import React from "react";
import { View, Text, Pressable, StyleSheet, Switch } from "react-native";
import Icon from "react-native-vector-icons/FontAwesome";

type Props = {
  greeting?: string;
  title?: string;
  onPressProfile?: () => void;

  showDivider?: boolean;

  showLocation?: boolean;
  locationLabel?: string;
  locationValue?: string;

  locationEnabled?: boolean;
  onToggleLocation?: (value: boolean) => void;
};

export default function HomeHeader({
  greeting = "Hi!",
  title = "WalkBuddy",
  onPressProfile,

  showDivider = true,

  showLocation = true,
  locationLabel = "LOCATION",
  locationValue = "",
  locationEnabled = false,
  onToggleLocation,
}: Props) {
  return (
    <View style={styles.wrap}>
      <View style={styles.headerRow}>
        <Text style={styles.greeting} numberOfLines={1}>
          {greeting}
        </Text>

        <Text style={styles.title} numberOfLines={1}>
          {title}
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
          <Text style={styles.locationLabel}>{locationLabel}</Text>

          <View style={styles.locationOuterCard}>
            <View style={styles.locationInnerRow}>
              <Text style={styles.locationValue} numberOfLines={1}>
                {locationValue}
              </Text>

              <Switch
                value={!!locationEnabled}
                onValueChange={(v) => onToggleLocation?.(v)}
                trackColor={{ false: "#23384d", true: "#2d4b66" }}
                thumbColor={locationEnabled ? tokens.gold : "#9aa8b6"}
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
