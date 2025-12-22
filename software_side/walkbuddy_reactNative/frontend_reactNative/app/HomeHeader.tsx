import { View, Text, Pressable, StyleSheet } from "react-native";
import Icon from "react-native-vector-icons/FontAwesome";

type Props = {
  greeting: string;
  title: string;
  onPressProfile: () => void;
};

export default function HomeHeader({ greeting, title, onPressProfile }: Props) {
  return (
    <View style={styles.header}>
      <Text style={styles.greeting}>{greeting}</Text>

      <Text style={styles.title}>{title}</Text>

      <Pressable onPress={onPressProfile} accessibilityLabel="Profile">
        <Icon name="user-circle" size={26} />
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 16,
  },
  greeting: {
    fontSize: 14,
  },
  title: {
    fontSize: 18,
    fontWeight: "600",
  },
});
