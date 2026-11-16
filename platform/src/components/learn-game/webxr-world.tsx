"use client";

import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import type * as THREE from "three";
import type { MissionChoice, MissionStep, GridPosition } from "@/data/learn-game";
import { gridToWorld, createWorldScene } from "@/components/learn-game/world-scene";

interface WebXRWorldProps {
  position: GridPosition;
  target: GridPosition;
  stage: number;
  step: MissionStep;
  choices: readonly MissionChoice[];
  canChoose: boolean;
  restored: boolean;
  feedback: { correct: boolean; message: string } | null;
  onMove: (position: GridPosition) => void;
  onChoose: (choice: MissionChoice) => void;
  onKeyDown: (event: KeyboardEvent<HTMLDivElement>) => void;
  onXRActiveChange: (active: boolean) => void;
  onXRSupportChange: (supported: boolean) => void;
}

export function WebXRWorld({
  position,
  target,
  stage,
  step,
  choices,
  canChoose,
  restored,
  feedback,
  onMove,
  onChoose,
  onKeyDown,
  onXRActiveChange,
  onXRSupportChange,
}: WebXRWorldProps) {
  const hostRef = useRef<HTMLDivElement>(null);
  const stateRef = useRef<WebXRWorldProps>({
    position,
    target,
    stage,
    step,
    choices,
    canChoose,
    restored,
    feedback,
    onMove,
    onChoose,
    onKeyDown,
    onXRActiveChange,
    onXRSupportChange,
  });
  const updatePanelRef = useRef<(() => void) | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  stateRef.current = {
    position,
    target,
    stage,
    step,
    choices,
    canChoose,
    restored,
    feedback,
    onMove,
    onChoose,
    onKeyDown,
    onXRActiveChange,
    onXRSupportChange,
  };

  useEffect(() => {
    let disposed = false;
    let cleanup: (() => void) | undefined;

    void Promise.all([
      import("three"),
      import("three/addons/controls/OrbitControls.js"),
      import("three/addons/webxr/VRButton.js"),
    ])
      .then(([THREE, { OrbitControls }, { VRButton }]) => {
        const host = hostRef.current;
        if (disposed || !host) return;

        const initial = stateRef.current;
        if (navigator.xr) {
          void navigator.xr
            .isSessionSupported("immersive-vr")
            .then((supported) => {
              if (!disposed) stateRef.current.onXRSupportChange(supported);
            })
            .catch((error: unknown) => {
              if (!disposed) stateRef.current.onXRSupportChange(false);
              console.error("Could not check immersive WebXR support.", error);
            });
        } else {
          stateRef.current.onXRSupportChange(false);
        }

        const world = createWorldScene(
          THREE,
          initial.step,
          initial.choices,
          initial.canChoose,
          initial.restored,
          initial.feedback
        );
        const renderer = new THREE.WebGLRenderer({
          antialias: true,
          alpha: false,
        });
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        renderer.shadowMap.enabled = true;
        renderer.shadowMap.type = THREE.PCFShadowMap;
        renderer.outputColorSpace = THREE.SRGBColorSpace;
        renderer.xr.enabled = true;
        renderer.domElement.setAttribute("role", "img");
        renderer.domElement.setAttribute(
          "aria-label",
          "Interactive 3D Caatinga landscape. Click ground tiles to move."
        );
        renderer.domElement.style.display = "block";
        renderer.domElement.style.width = "100%";
        renderer.domElement.style.height = "100%";
        host.appendChild(renderer.domElement);

        const vrButton = VRButton.createButton(renderer, {
          optionalFeatures: ["hand-tracking"],
        });
        host.appendChild(vrButton);

        const controls = new OrbitControls(
          world.camera,
          renderer.domElement
        );
        controls.target.set(0, 0, -4.5);
        controls.enableDamping = true;
        controls.dampingFactor = 0.08;
        controls.minDistance = 5;
        controls.maxDistance = 24;
        controls.maxPolarAngle = Math.PI / 2.03;

        const raycaster = new THREE.Raycaster();
        const pointer = new THREE.Vector2();
        const controllerObjects: THREE.Group[] = [];
        const interactiveObjects: THREE.Object3D[] = [
          ...world.tileMeshes,
          ...world.actionMeshes,
        ];
        let pointerStart: [number, number] | null = null;
        const cameraRotation = new THREE.Matrix4();

        const chooseIntersection = (intersections: THREE.Intersection[]) => {
          const hit = intersections.find(
            (intersection) => intersection.object.userData.interaction
          );
          if (!hit) return;
          const object = hit.object;
          if (object.userData.interaction === "tile") {
            const gridPosition = object.userData.gridPosition as GridPosition;
            stateRef.current.onMove(gridPosition);
          } else if (
            object.userData.interaction === "choice" &&
            stateRef.current.canChoose
          ) {
            const choice = stateRef.current.choices[
              object.userData.choiceIndex as number
            ];
            if (choice) stateRef.current.onChoose(choice);
          }
        };

        const raycastController = (controller: THREE.Group) => {
          controller.updateMatrixWorld(true);
          raycaster.ray.origin.setFromMatrixPosition(controller.matrixWorld);
          cameraRotation.extractRotation(controller.matrixWorld);
          raycaster.ray.direction
            .set(0, 0, -1)
            .applyMatrix4(cameraRotation)
            .normalize();
          chooseIntersection(
            raycaster.intersectObjects(interactiveObjects, false)
          );
        };

        for (let index = 0; index < 2; index += 1) {
          const controller = renderer.xr.getController(index);
          controller.addEventListener("selectstart", () =>
            raycastController(controller)
          );
          const ray = new THREE.Line(
            new THREE.BufferGeometry().setFromPoints([
              new THREE.Vector3(0, 0, 0),
              new THREE.Vector3(0, 0, -1),
            ]),
            new THREE.LineBasicMaterial({
              color: "#fff1a4",
              transparent: true,
              opacity: 0.8,
            })
          );
          ray.scale.z = 8;
          controller.add(ray);
          world.scene.add(controller);
          controllerObjects.push(controller);
        }

        const onPointerDown = (event: PointerEvent) => {
          pointerStart = [event.clientX, event.clientY];
        };
        const onPointerUp = (event: PointerEvent) => {
          if (!pointerStart) return;
          const distance = Math.hypot(
            event.clientX - pointerStart[0],
            event.clientY - pointerStart[1]
          );
          pointerStart = null;
          if (distance > 8) return;

          const bounds = renderer.domElement.getBoundingClientRect();
          pointer.x = ((event.clientX - bounds.left) / bounds.width) * 2 - 1;
          pointer.y = -((event.clientY - bounds.top) / bounds.height) * 2 + 1;
          raycaster.setFromCamera(pointer, world.camera);
          chooseIntersection(
            raycaster.intersectObjects(interactiveObjects, false)
          );
        };
        renderer.domElement.addEventListener("pointerdown", onPointerDown);
        renderer.domElement.addEventListener("pointerup", onPointerUp);

        const onSessionStart = () => {
          controls.enabled = false;
          world.missionPanel.visible = true;
          stateRef.current.onXRActiveChange(true);
        };
        const onSessionEnd = () => {
          controls.enabled = true;
          world.missionPanel.visible = false;
          stateRef.current.onXRActiveChange(false);
        };
        renderer.xr.addEventListener("sessionstart", onSessionStart);
        renderer.xr.addEventListener("sessionend", onSessionEnd);

        const resize = () => {
          const bounds = host.getBoundingClientRect();
          if (bounds.width <= 0 || bounds.height <= 0) return;
          world.camera.aspect = bounds.width / bounds.height;
          world.camera.updateProjectionMatrix();
          if (!renderer.xr.isPresenting) {
            renderer.setSize(bounds.width, bounds.height, false);
          }
        };
        const resizeObserver = new ResizeObserver(resize);
        resizeObserver.observe(host);
        resize();

        renderer.setAnimationLoop(() => {
          const current = stateRef.current;
          controls.update();
          const destination = gridToWorld(THREE, current.position);
          world.player.position.lerp(destination, 0.18);
          const targetPoint = gridToWorld(THREE, current.target);
          world.marker.position.set(targetPoint.x, 0.03, targetPoint.z);
          world.marker.visible = !current.restored;
          world.restoration.visible = current.restored;
          world.radarSweep.visible = current.stage === 0;
          world.degradationMarkers.visible = current.stage === 1;
          world.satellite.rotation.y += 0.0015;
          renderer.render(world.scene, world.camera);
        });

        updatePanelRef.current = () => {
          world.updateMissionPanel(
            stateRef.current.step,
            stateRef.current.choices,
            stateRef.current.canChoose,
            stateRef.current.restored,
            stateRef.current.feedback
          );
          interactiveObjects.splice(
            world.tileMeshes.length,
            interactiveObjects.length - world.tileMeshes.length,
            ...world.actionMeshes
          );
        };

        cleanup = () => {
          updatePanelRef.current = null;
          renderer.setAnimationLoop(null);
          renderer.xr.removeEventListener("sessionstart", onSessionStart);
          renderer.xr.removeEventListener("sessionend", onSessionEnd);
          renderer.domElement.removeEventListener("pointerdown", onPointerDown);
          renderer.domElement.removeEventListener("pointerup", onPointerUp);
          resizeObserver.disconnect();
          controls.dispose();
          for (const controller of controllerObjects) {
            world.scene.remove(controller);
          }
          vrButton.remove();
          renderer.domElement.remove();
          world.scene.traverse((object) => {
            if (!(object instanceof THREE.Mesh || object instanceof THREE.Line)) {
              return;
            }
            object.geometry.dispose();
            const materials = Array.isArray(object.material)
              ? object.material
              : [object.material];
            for (const material of materials) {
              for (const value of Object.values(material)) {
                if (value instanceof THREE.Texture) value.dispose();
              }
              material.dispose();
            }
          });
          renderer.dispose();
        };

        updatePanelRef.current();
      })
      .catch((error: unknown) => {
        if (!disposed) {
          setLoadError(
            error instanceof Error ? error.message : "Unknown WebXR error"
          );
        }
      });

    return () => {
      disposed = true;
      cleanup?.();
    };
  }, []);

  useEffect(() => {
    updatePanelRef.current?.();
  }, [step, choices, canChoose, restored, feedback]);

  return (
    <div
      ref={hostRef}
      className="relative aspect-[640/420] w-full overflow-hidden rounded-xl [&_canvas]:touch-none"
      role="group"
      tabIndex={0}
      onKeyDown={onKeyDown}
      onPointerDown={(event) => event.currentTarget.focus()}
      aria-label="3D game board. Click a ground tile to move or enter VR to use a controller."
    >
      {loadError ? (
        <p
          role="alert"
          className="absolute inset-0 z-10 flex items-center justify-center bg-[#b8d6d3] px-6 text-center text-sm text-[#220f08]"
        >
          The 3D scene could not load: {loadError}
        </p>
      ) : null}
    </div>
  );
}
