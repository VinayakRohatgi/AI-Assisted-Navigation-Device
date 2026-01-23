// app/lib/locationSaver.tsx

/**
 * Location State Provider (temporary navigation simulation)
 *
 * This provider owns all location-related state used by the shared Header
 * and any components that depend on “where the user is” or “where they are going”.
 *
 * Current responsibilities:
 * - Tracks the user’s currentLocation (string)
 * - Tracks an optional destination (string | null)
 * - Exposes a view preference (preferDestinationView) used by the Header switch
 *   to toggle between displaying Location vs Destination
 * - Listens to route changes via Expo Router and re-seeds mock data on navigation
 *
 * Behaviour:
 * - On each route change, location data is re-generated
 * - Location / Destination alternates every roll (for visual verification)
 * - If a destination exists and is preferred, currentLocation is synced to it
 *   to preserve compatibility with existing save logic
 *
 * Important notes:
 * - This file DOES NOT perform real geolocation or routing
 * - All values are currently mock/generated and intended for UI wiring only
 * - Existing save / footer logic relies on `currentLocation` and must not break
 *
 * Future intent:
 * - Replace mock generators with real GPS / indoor navigation data
 * - Destination will be driven by internal/external navigation components
 * - Profile data (name, preferences) will eventually feed the Header greeting
 */

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { useSegments } from "expo-router";

type LocationContextType = {
  currentLocation: string;
  destination: string | null;

  setCurrentLocation: (value: string) => void;
  setDestination: (value: string | null) => void;

  // Header switch (view preference only)
  preferDestinationView: boolean;
  setPreferDestinationView: (value: boolean) => void;

  // Dev / testing helpers
  seedMockLocations: () => void;
  clearDestination: () => void;

  // Route info (for future use)
  currentRouteKey: string;
  previousRouteKey: string;
};

const CurrentLocationContext = createContext<LocationContextType | null>(null);

// Toggle this off when real location/navigation is wired
const ENABLE_ROUTE_REROLL = true;

function pickRandom<T>(arr: T[]) {
  return arr[Math.floor(Math.random() * arr.length)];
}

const MOCK_EXTERNAL_ADDRESSES = [
  "12 Riverstone Ave, Geelong VIC",
  "88 Bayview Rd, Docklands VIC",
  "3 Wattle Grove, Footscray VIC",
  "145 Station St, Burwood VIC",
  "22 Highridge Cres, Clayton VIC",
  "9 Lantern Way, Southbank VIC",
  "301 Princes Hwy, Dandenong VIC",
  "6 Seafarers Ln, Melbourne VIC",
  "17 Oceanview Dr, Torquay VIC",
  "54 Greenhill Rd, Kew VIC",
];

const MOCK_INTERNAL_LOCATIONS = [
  "Science Section, Deakin Library",
  "Main Entrance, Deakin Waterfront",
  "Student Hub, Level 2",
  "Quiet Study Zone, Level 3",
  "Café Area, Ground Floor",
  "Reception Desk, Building A",
  "Lecture Theatre 1 (LT1)",
  "Computer Lab, Room 2.15",
  "Accessible Toilets, Near Lift",
  "Atrium, Central Walkway",
];

function randomLocationString() {
  return Math.random() < 0.5
    ? pickRandom(MOCK_EXTERNAL_ADDRESSES)
    : pickRandom(MOCK_INTERNAL_LOCATIONS);
}

export function CurrentLocationProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const segments = useSegments();

  const [currentLocation, setCurrentLocation] = useState("");
  const [destination, setDestination] = useState<string | null>(null);

  // Header switch (view preference)
  const [preferDestinationView, setPreferDestinationView] = useState(false);

  // Route tracking
  const [currentRouteKey, setCurrentRouteKey] = useState("");
  const [previousRouteKey, setPreviousRouteKey] = useState("");

  const lastRouteKeyRef = useRef<string>("");
  const rollRef = useRef<number>(0); // alternates on each roll

  const clearDestination = useCallback(() => {
    setDestination(null);
    setPreferDestinationView(false);
  }, []);

  /**
   * Alternates every roll:
   * odd rolls -> LOCATION only
   * even rolls -> DESTINATION active
   */
  const seedMockLocations = useCallback(() => {
    rollRef.current += 1;

    const baseLocation = randomLocationString();

    const useDestinationThisRoll = rollRef.current % 2 === 0;

    if (!useDestinationThisRoll) {
      // LOCATION roll
      setDestination(null);
      setPreferDestinationView(false);
      setCurrentLocation(baseLocation);
      return;
    }

    // DESTINATION roll
    const dest = randomLocationString();
    setDestination(dest);
    setPreferDestinationView(true);

    // Backward compatibility: currentLocation always equals what's displayed
    setCurrentLocation(dest);
  }, []);

  /**
   * Keep currentLocation in sync when user flips the header switch.
   * This preserves Footer save behaviour (Footer reads currentLocation).
   */
  useEffect(() => {
    if (preferDestinationView && destination) {
      setCurrentLocation(destination);
    }

    if (!preferDestinationView && destination) {
      // When toggling back, we need a "real" location value to show.
      // If currentLocation is currently the destination, reroll a base location.
      // This keeps behaviour predictable during testing.
      // You can later replace this with actual geolocation.
      if (currentLocation === destination) {
        setCurrentLocation(randomLocationString());
      }
    }
    // Intentionally include currentLocation so the equality check works.
  }, [preferDestinationView, destination, currentLocation]);

  /**
   * Route change detection -> reroll
   */
  useEffect(() => {
    const routeKey = segments.join("/");

    if (lastRouteKeyRef.current === "") {
      lastRouteKeyRef.current = routeKey;
      setCurrentRouteKey(routeKey);

      if (ENABLE_ROUTE_REROLL) {
        seedMockLocations();
      }
      return;
    }

    if (routeKey !== lastRouteKeyRef.current) {
      const prev = lastRouteKeyRef.current;
      lastRouteKeyRef.current = routeKey;

      setPreviousRouteKey(prev);
      setCurrentRouteKey(routeKey);

      if (ENABLE_ROUTE_REROLL) {
        seedMockLocations();
      }
    }
  }, [segments, seedMockLocations]);

  const value = useMemo<LocationContextType>(() => {
    return {
      currentLocation,
      destination,

      setCurrentLocation,
      setDestination,

      preferDestinationView,
      setPreferDestinationView,

      seedMockLocations,
      clearDestination,

      currentRouteKey,
      previousRouteKey,
    };
  }, [
    currentLocation,
    destination,
    preferDestinationView,
    seedMockLocations,
    clearDestination,
    currentRouteKey,
    previousRouteKey,
  ]);

  return (
    <CurrentLocationContext.Provider value={value}>
      {children}
    </CurrentLocationContext.Provider>
  );
}

export function useCurrentLocation() {
  const context = useContext(CurrentLocationContext);

  if (!context) {
    throw new Error(
      "useCurrentLocation must be used inside CurrentLocationProvider"
    );
  }

  return context;
}
