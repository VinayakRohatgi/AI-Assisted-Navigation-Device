import { View, Text, Pressable, StyleSheet } from "react-native";
import Icon from "react-native-vector-icons/FontAwesome";

type Props = {
  greeting: string;
  title: string;
  onPressProfile: () => void;
};

export default function HomeHeader({ greeting, title, onPressProfile }: Props) {
  return (
    <View style={styles.headerRow}>
      <Text style={styles.greeting}>{greeting}</Text>

      <Text style={styles.title}>{title}</Text>

      <Pressable onPress={onPressProfile} accessibilityLabel="Account">
        <Icon name="user-circle" size={26} color={tokens.gold} />
      </Pressable>
    </View>
  );
}

const tokens = {
  text: "#e8eef6",
  gold: "#f2a900",
};

const styles = StyleSheet.create({
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
  },

  title: {
    color: tokens.text,
    fontSize: 22,
    fontWeight: "800",
  },
});
