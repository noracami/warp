<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import L from "leaflet";
  import "leaflet/dist/leaflet.css";
  import { loadMapView, saveMapView } from "./storage";

  interface Props {
    marker: [number, number] | null;
    pending: [number, number] | null;
    onMapClick: (lat: number, lng: number) => void;
    onPendingCommit: () => void;
    onReady?: (map: L.Map) => void;
  }
  let { marker, pending, onMapClick, onPendingCommit, onReady }: Props = $props();

  let container: HTMLDivElement;
  let map: L.Map | undefined;
  let markerLayer: L.CircleMarker | undefined;
  let pendingLayer: L.CircleMarker | undefined;

  const DEFAULT_VIEW = { lat: 25.033964, lng: 121.564472, zoom: 14 };

  onMount(() => {
    const initial = loadMapView() ?? DEFAULT_VIEW;
    map = L.map(container, { zoomControl: true }).setView(
      [initial.lat, initial.lng],
      initial.zoom,
    );
    onReady?.(map);

    L.tileLayer("https://basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
      subdomains: "abcd",
      maxZoom: 19,
    }).addTo(map);

    map.on("click", (e: L.LeafletMouseEvent) => {
      const wrapped = e.latlng.wrap();
      onMapClick(wrapped.lat, wrapped.lng);
    });

    map.on("moveend zoomend", () => {
      if (!map) return;
      const c = map.getCenter();
      saveMapView({ lat: c.lat, lng: c.lng, zoom: map.getZoom() });
    });
  });

  onDestroy(() => {
    map?.remove();
    map = undefined;
  });

  $effect(() => {
    if (!map) return;
    if (marker) {
      if (!markerLayer) {
        markerLayer = L.circleMarker(marker, {
          radius: 8,
          color: "#fff",
          weight: 2,
          fillColor: "#e11d48",
          fillOpacity: 1,
        }).addTo(map);
      } else {
        markerLayer.setLatLng(marker);
      }
    } else if (markerLayer) {
      markerLayer.remove();
      markerLayer = undefined;
    }
  });

  $effect(() => {
    if (!map) return;
    if (pending) {
      if (!pendingLayer) {
        pendingLayer = L.circleMarker(pending, {
          radius: 9,
          color: "#fde047",
          weight: 2,
          fillColor: "#facc15",
          fillOpacity: 0.7,
          className: "warp-pending-marker",
        })
          .addTo(map)
          .on("click", (e: L.LeafletMouseEvent) => {
            L.DomEvent.stopPropagation(e);
            onPendingCommit();
          });
      } else {
        pendingLayer.setLatLng(pending);
      }
    } else if (pendingLayer) {
      pendingLayer.remove();
      pendingLayer = undefined;
    }
  });
</script>

<div bind:this={container} class="map-container"></div>

<style>
  .map-container {
    width: 100%;
    height: 100%;
  }

  :global(.leaflet-container) {
    background: #0f1116;
    font-family: inherit;
  }

  :global(.leaflet-control-attribution) {
    background: rgba(26, 29, 36, 0.85) !important;
    color: #9ca3af !important;
  }

  :global(.leaflet-control-attribution a) {
    color: #d1d5db !important;
  }

  :global(.leaflet-control-zoom a) {
    background: #1a1d24 !important;
    color: #e5e7eb !important;
    border-color: #2a2d35 !important;
  }

  :global(.leaflet-control-zoom a:hover) {
    background: #2a2d35 !important;
  }

  :global(.warp-pending-marker) {
    animation: warpPulse 1.2s ease-in-out infinite;
    cursor: pointer;
  }

  @keyframes warpPulse {
    0%,
    100% {
      opacity: 0.7;
      stroke-width: 2;
    }
    50% {
      opacity: 1;
      stroke-width: 4;
    }
  }
</style>
