import type * as THREE from "three";
import type {
  GridPosition,
  MissionChoice,
  MissionStep,
} from "@/data/learn-game";

const COLUMNS = 9;
const ROWS = 7;
const TILE_SIZE = 1.12;

export interface WorldScene {
  scene: THREE.Scene;
  camera: THREE.PerspectiveCamera;
  player: THREE.Group;
  marker: THREE.Group;
  satellite: THREE.Group;
  radarSweep: THREE.Group;
  degradationMarkers: THREE.Group;
  restoration: THREE.Group;
  tileMeshes: THREE.Mesh[];
  missionPanel: THREE.Group;
  actionMeshes: THREE.Mesh[];
  updateMissionPanel: (
    step: MissionStep,
    choices: readonly MissionChoice[],
    canChoose: boolean,
    complete: boolean,
    feedback: { correct: boolean; message: string } | null
  ) => void;
}

export function gridToWorld(
  THREE: typeof import("three"),
  position: GridPosition
): THREE.Vector3 {
  return new THREE.Vector3(
    (position.column - (COLUMNS - 1) / 2) * TILE_SIZE,
    0.05,
    (position.row - (ROWS - 1) / 2) * TILE_SIZE - 5
  );
}

function standard(
  THREE: typeof import("three"),
  color: string,
  roughness = 0.9
): THREE.MeshStandardMaterial {
  return new THREE.MeshStandardMaterial({ color, roughness });
}

function addBox(
  THREE: typeof import("three"),
  parent: THREE.Group,
  size: [number, number, number],
  color: string,
  position: [number, number, number]
): THREE.Mesh {
  const mesh = new THREE.Mesh(
    new THREE.BoxGeometry(...size),
    standard(THREE, color)
  );
  mesh.position.set(...position);
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  parent.add(mesh);
  return mesh;
}

function addCactus(
  THREE: typeof import("three"),
  parent: THREE.Group,
  x: number,
  z: number,
  scale = 1
): void {
  const cactus = new THREE.Group();
  cactus.position.set(x, 0.04, z);
  cactus.scale.setScalar(scale);
  const green = standard(THREE, "#386449");
  const lightGreen = standard(THREE, "#557b51");

  const trunk = new THREE.Mesh(
    new THREE.CylinderGeometry(0.13, 0.16, 1.15, 6),
    green
  );
  trunk.position.y = 0.6;
  trunk.castShadow = true;
  cactus.add(trunk);

  const arm = new THREE.Mesh(
    new THREE.CylinderGeometry(0.075, 0.09, 0.55, 6),
    lightGreen
  );
  arm.position.set(-0.2, 0.57, 0);
  arm.rotation.z = Math.PI / 2;
  cactus.add(arm);

  const leftArm = new THREE.Mesh(
    new THREE.CylinderGeometry(0.07, 0.09, 0.4, 6),
    green
  );
  leftArm.position.set(-0.43, 0.73, 0);
  cactus.add(leftArm);

  const rightArm = new THREE.Mesh(
    new THREE.CylinderGeometry(0.07, 0.09, 0.38, 6),
    lightGreen
  );
  rightArm.position.set(0.19, 0.79, 0);
  rightArm.rotation.z = Math.PI / 2;
  cactus.add(rightArm);

  const rightTip = new THREE.Mesh(
    new THREE.CylinderGeometry(0.06, 0.08, 0.28, 6),
    green
  );
  rightTip.position.set(0.34, 0.91, 0);
  cactus.add(rightTip);
  parent.add(cactus);
}

function addPerson(
  THREE: typeof import("three"),
  parent: THREE.Group,
  x: number,
  z: number,
  shirt: string,
  scale = 1
): THREE.Group {
  const person = new THREE.Group();
  person.position.set(x, 0.04, z);
  person.scale.setScalar(scale);
  const body = new THREE.Mesh(
    new THREE.CylinderGeometry(0.14, 0.2, 0.52, 7),
    standard(THREE, shirt)
  );
  body.position.y = 0.39;
  body.castShadow = true;
  person.add(body);

  const head = new THREE.Mesh(
    new THREE.SphereGeometry(0.16, 8, 6),
    standard(THREE, "#bd855f")
  );
  head.position.y = 0.78;
  head.castShadow = true;
  person.add(head);

  const hat = new THREE.Mesh(
    new THREE.CylinderGeometry(0.22, 0.2, 0.08, 8),
    standard(THREE, "#d5b66d")
  );
  hat.position.y = 0.94;
  person.add(hat);
  parent.add(person);
  return person;
}

function makeTexture(
  THREE: typeof import("three"),
  draw: (context: CanvasRenderingContext2D) => void,
  width = 768,
  height = 1024
): THREE.CanvasTexture {
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext("2d");
  if (!context) throw new Error("Could not create the WebXR interface texture.");
  draw(context);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  return texture;
}

function wrapText(
  context: CanvasRenderingContext2D,
  text: string,
  x: number,
  y: number,
  maxWidth: number,
  lineHeight: number
): number {
  let line = "";
  for (const word of text.split(/\s+/)) {
    const candidate = line ? `${line} ${word}` : word;
    if (context.measureText(candidate).width > maxWidth && line) {
      context.fillText(line, x, y);
      y += lineHeight;
      line = word;
    } else {
      line = candidate;
    }
  }
  if (line) {
    context.fillText(line, x, y);
    y += lineHeight;
  }
  return y;
}

function createPanelTexture(
  THREE: typeof import("three"),
  step: MissionStep,
  complete: boolean,
  feedback: { correct: boolean; message: string } | null
): THREE.CanvasTexture {
  return makeTexture(THREE, (context) => {
    context.fillStyle = "#241912";
    context.fillRect(0, 0, 768, 1024);
    context.strokeStyle = "#d5b66d";
    context.lineWidth = 12;
    context.strokeRect(10, 10, 748, 1004);

    context.fillStyle = "#f4d875";
    context.font = "bold 30px system-ui, sans-serif";
    context.fillText("DESERT SENTINEL · FIELD MISSION", 52, 76);

    let y = 150;
    context.fillStyle = "#fff8e9";
    context.font = "bold 56px system-ui, sans-serif";
    y = wrapText(
      context,
      complete ? "Mission complete" : step.title,
      52,
      y,
      660,
      64
    );

    context.fillStyle = "#e7d8b8";
    context.font = "34px system-ui, sans-serif";
    y += 14;
    y = wrapText(
      context,
      complete
        ? "The restoration plot is growing. Keep monitoring: restoration takes time."
        : `${step.area}: ${step.prompt}`,
      52,
      y,
      660,
      46
    );

    if (!complete) {
      context.fillStyle = "#c9b99b";
      context.font = "28px system-ui, sans-serif";
      y += 18;
      y = wrapText(context, `Field clue: ${step.clue}`, 52, y, 660, 38);
      if (feedback) {
        context.fillStyle = feedback.correct ? "#b8d79c" : "#f2ae8a";
        context.font = "bold 29px system-ui, sans-serif";
        y += 18;
        wrapText(context, feedback.message, 52, y, 660, 38);
      }
    } else {
      context.fillStyle = "#b8d79c";
      context.font = "bold 32px system-ui, sans-serif";
      context.fillText("Native plants are taking root.", 52, y + 34);
    }

    context.fillStyle = "#c9b99b";
    context.font = "26px system-ui, sans-serif";
    context.fillText(
      complete ? "Use the VR button to exit." : "Point a controller and press its trigger.",
      52,
      966
    );
  });
}

function createActionTexture(
  THREE: typeof import("three"),
  choice: MissionChoice,
  canChoose: boolean
): THREE.CanvasTexture {
  return makeTexture(
    THREE,
    (context) => {
      context.fillStyle = canChoose ? "#775126" : "#574b3b";
      context.fillRect(0, 0, 768, 240);
      context.strokeStyle = canChoose ? "#f1d275" : "#8a7a66";
      context.lineWidth = 8;
      context.strokeRect(5, 5, 758, 230);
      context.fillStyle = canChoose ? "#fff8e9" : "#c2b8a8";
      context.font = "bold 39px system-ui, sans-serif";
      wrapText(context, choice.label, 34, 83, 700, 47);
      context.font = "27px system-ui, sans-serif";
      context.fillStyle = canChoose ? "#ead7b3" : "#a99c8b";
      context.fillText(
        canChoose ? "Select this action" : "Move closer to the signal first",
        34,
        202
      );
    },
    768,
    240
  );
}

export function createWorldScene(
  THREE: typeof import("three"),
  initialStep: MissionStep,
  initialChoices: readonly MissionChoice[],
  canChoose: boolean,
  complete: boolean,
  feedback: { correct: boolean; message: string } | null
): WorldScene {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color("#b8d6d3");
  scene.fog = new THREE.Fog("#b8d6d3", 19, 38);

  const camera = new THREE.PerspectiveCamera(54, 1, 0.1, 80);
  camera.position.set(0, 10.5, 10.5);
  camera.lookAt(0, 0, -4.5);
  scene.add(camera);

  scene.add(new THREE.HemisphereLight("#e3f0e2", "#785536", 2.2));
  const sunLight = new THREE.DirectionalLight("#fff1cc", 3.2);
  sunLight.position.set(-6, 12, 5);
  sunLight.castShadow = true;
  sunLight.shadow.mapSize.set(1024, 1024);
  sunLight.shadow.camera.left = -12;
  sunLight.shadow.camera.right = 12;
  sunLight.shadow.camera.top = 15;
  sunLight.shadow.camera.bottom = -15;
  scene.add(sunLight);

  const world = new THREE.Group();
  scene.add(world);
  const ground = new THREE.Mesh(
    new THREE.PlaneGeometry(80, 80),
    standard(THREE, "#c8a576")
  );
  ground.rotation.x = -Math.PI / 2;
  ground.position.set(0, -0.2, -4.5);
  ground.receiveShadow = true;
  world.add(ground);

  const tileMeshes: THREE.Mesh[] = [];
  for (let row = 0; row < ROWS; row += 1) {
    for (let column = 0; column < COLUMNS; column += 1) {
      const dryPatch = column >= 5 && row <= 3;
      const fertile = (column + row) % 4 === 1 || (column < 3 && row > 3);
      const color = dryPatch
        ? "#c88d54"
        : fertile
          ? "#929d61"
          : "#b38a58";
      const tile = new THREE.Mesh(
        new THREE.BoxGeometry(1.06, 0.2, 1.06),
        standard(THREE, color)
      );
      const position = gridToWorld(THREE, { column, row });
      tile.position.set(position.x, -0.08, position.z);
      tile.receiveShadow = true;
      tile.userData.gridPosition = { column, row };
      tile.userData.interaction = "tile";
      world.add(tile);
      tileMeshes.push(tile);

      if (dryPatch && (column + row) % 3 === 0) {
        const crack = new THREE.Mesh(
          new THREE.BoxGeometry(0.34, 0.012, 0.025),
          standard(THREE, "#efd39a")
        );
        crack.position.set(position.x - 0.08, 0.027, position.z + 0.1);
        crack.rotation.y = 0.42;
        world.add(crack);
      }
    }
  }

  const mesaColors = ["#9aada2", "#839b94", "#b39a76"];
  for (let index = 0; index < 5; index += 1) {
    const mesa = new THREE.Mesh(
      new THREE.ConeGeometry(2.4 + (index % 2) * 0.7, 3.4, 5),
      standard(THREE, mesaColors[index % mesaColors.length])
    );
    mesa.position.set(-10 + index * 5, 1, -14 - (index % 2) * 2);
    mesa.rotation.y = index * 0.37;
    world.add(mesa);
  }

  const sun = new THREE.Mesh(
    new THREE.SphereGeometry(0.72, 16, 12),
    new THREE.MeshBasicMaterial({ color: "#f4d477" })
  );
  sun.position.set(7.5, 7, -13);
  world.add(sun);

  const satellite = new THREE.Group();
  satellite.position.set(-0.5, 5.2, -5.2);
  const satelliteBody = new THREE.Mesh(
    new THREE.BoxGeometry(0.45, 0.34, 0.45),
    standard(THREE, "#d7d4cb", 0.5)
  );
  satellite.add(satelliteBody);
  for (const side of [-1, 1]) {
    const panel = new THREE.Mesh(
      new THREE.BoxGeometry(0.72, 0.035, 0.42),
      standard(THREE, "#3d6c7d", 0.4)
    );
    panel.position.x = side * 0.63;
    satellite.add(panel);
  }
  const antenna = new THREE.Mesh(
    new THREE.ConeGeometry(0.12, 0.22, 8),
    standard(THREE, "#ddd4ba")
  );
  antenna.position.y = -0.25;
  satellite.add(antenna);
  world.add(satellite);

  const radarSweep = new THREE.Group();
  const radarMaterial = new THREE.LineBasicMaterial({
    color: "#52d7dc",
    transparent: true,
    opacity: 0.68,
  });
  const radarTarget = gridToWorld(THREE, initialStep.target);
  for (const offset of [-0.45, 0.45]) {
    const beam = new THREE.Line(
      new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(satellite.position.x + offset, satellite.position.y, satellite.position.z),
        new THREE.Vector3(radarTarget.x, 0.18, radarTarget.z),
      ]),
      radarMaterial
    );
    radarSweep.add(beam);
  }
  world.add(radarSweep);

  const degradationMarkers = new THREE.Group();
  for (const position of [
    { column: 5, row: 1 },
    { column: 7, row: 2 },
    { column: 6, row: 3 },
  ]) {
    const point = gridToWorld(THREE, position);
    const pin = new THREE.Group();
    pin.position.set(point.x, 0.12, point.z);
    const dot = new THREE.Mesh(
      new THREE.SphereGeometry(0.12, 10, 8),
      new THREE.MeshStandardMaterial({
        color: "#c55538",
        emissive: "#6d2011",
        emissiveIntensity: 0.2,
      })
    );
    dot.position.y = 0.18;
    pin.add(dot);
    const stem = new THREE.Mesh(
      new THREE.CylinderGeometry(0.025, 0.025, 0.35, 6),
      standard(THREE, "#813f2e")
    );
    pin.add(stem);
    degradationMarkers.add(pin);
  }
  world.add(degradationMarkers);

  const restoration = new THREE.Group();
  for (const position of [
    { column: 1, row: 4 },
    { column: 2, row: 4 },
    { column: 3, row: 4 },
    { column: 4, row: 4 },
    { column: 1, row: 5 },
    { column: 3, row: 5 },
    { column: 4, row: 5 },
    { column: 5, row: 5 },
  ]) {
    const point = gridToWorld(THREE, position);
    const sapling = new THREE.Group();
    sapling.position.set(point.x, 0.02, point.z);
    const stem = new THREE.Mesh(
      new THREE.CylinderGeometry(0.025, 0.045, 0.45, 5),
      standard(THREE, "#66482e")
    );
    stem.position.y = 0.22;
    sapling.add(stem);
    const leaves = new THREE.Mesh(
      new THREE.DodecahedronGeometry(0.28, 0),
      standard(THREE, "#6b9455")
    );
    leaves.position.y = 0.52;
    leaves.castShadow = true;
    sapling.add(leaves);
    restoration.add(sapling);
  }
  restoration.visible = false;
  world.add(restoration);

  const positions = [
    { column: 1, row: 1, scale: 0.8 },
    { column: 7, row: 4, scale: 1.1 },
    { column: 3, row: 6, scale: 0.9 },
  ];
  for (const item of positions) {
    const point = gridToWorld(THREE, item);
    addCactus(THREE, world, point.x, point.z, item.scale);
  }

  const hutPosition = gridToWorld(THREE, { column: 7, row: 5 });
  const hut = new THREE.Group();
  hut.position.set(hutPosition.x, 0.02, hutPosition.z);
  addBox(THREE, hut, [1.1, 0.75, 0.85], "#e9d39f", [0, 0.4, 0]);
  const roof = new THREE.Mesh(
    new THREE.ConeGeometry(0.84, 0.48, 4),
    standard(THREE, "#804b32")
  );
  roof.position.y = 1;
  roof.rotation.y = Math.PI / 4;
  hut.add(roof);
  addBox(THREE, hut, [0.2, 0.44, 0.04], "#573a2a", [0, 0.24, 0.44]);
  world.add(hut);

  const partnerPosition = gridToWorld(THREE, { column: 6, row: 5 });
  addPerson(THREE, world, partnerPosition.x - 0.28, partnerPosition.z, "#a2510f", 0.82);
  addPerson(THREE, world, partnerPosition.x + 0.32, partnerPosition.z - 0.12, "#596d4d", 0.82);

  const player = addPerson(THREE, world, 0, 0, "#315d67", 0.94);
  player.position.copy(gridToWorld(THREE, { column: 1, row: 3 }));
  const marker = new THREE.Group();
  const ring = new THREE.Mesh(
    new THREE.TorusGeometry(0.48, 0.035, 8, 24),
    new THREE.MeshBasicMaterial({ color: "#f1cd63" })
  );
  ring.rotation.x = Math.PI / 2;
  ring.position.y = 0.08;
  marker.add(ring);
  const beacon = new THREE.Mesh(
    new THREE.CylinderGeometry(0.035, 0.035, 0.66, 6),
    new THREE.MeshBasicMaterial({ color: "#f1cd63" })
  );
  beacon.position.y = 0.47;
  marker.add(beacon);
  const beaconTop = new THREE.Mesh(
    new THREE.SphereGeometry(0.11, 10, 8),
    new THREE.MeshBasicMaterial({ color: "#fff1a4" })
  );
  beaconTop.position.y = 0.82;
  marker.add(beaconTop);
  world.add(marker);

  const missionPanel = new THREE.Group();
  missionPanel.visible = false;
  camera.add(missionPanel);
  missionPanel.position.set(0, 0, -2);
  const panelMaterial = new THREE.MeshBasicMaterial({
    color: "#ffffff",
    side: THREE.DoubleSide,
    transparent: false,
  });
  const panelSurface = new THREE.Mesh(
    new THREE.PlaneGeometry(1.62, 2.4),
    panelMaterial
  );
  missionPanel.add(panelSurface);
  const actionMeshes: THREE.Mesh[] = [];

  const updateMissionPanel = (
    step: MissionStep,
    choices: readonly MissionChoice[],
    canSelect: boolean,
    isComplete: boolean,
    answerFeedback: { correct: boolean; message: string } | null
  ) => {
    const nextTexture = createPanelTexture(
      THREE,
      step,
      isComplete,
      answerFeedback
    );
    if (panelMaterial.map) panelMaterial.map.dispose();
    panelMaterial.map = nextTexture;
    panelMaterial.needsUpdate = true;

    for (const mesh of actionMeshes) {
      missionPanel.remove(mesh);
      mesh.geometry.dispose();
      const material = mesh.material as THREE.MeshBasicMaterial;
      material.map?.dispose();
      material.dispose();
    }
    actionMeshes.length = 0;
    if (isComplete) return;

    choices.forEach((choice, index) => {
      const texture = createActionTexture(THREE, choice, canSelect);
      const button = new THREE.Mesh(
        new THREE.PlaneGeometry(1.38, 0.44),
        new THREE.MeshBasicMaterial({
          map: texture,
          transparent: false,
          side: THREE.DoubleSide,
        })
      );
      button.position.set(0, index === 0 ? -0.42 : -0.9, 0.015);
      button.userData.interaction = "choice";
      button.userData.choiceIndex = index;
      missionPanel.add(button);
      actionMeshes.push(button);
    });
  };
  updateMissionPanel(initialStep, initialChoices, canChoose, complete, feedback);

  return {
    scene,
    camera,
    player,
    marker,
    satellite,
    radarSweep,
    degradationMarkers,
    restoration,
    tileMeshes,
    missionPanel,
    actionMeshes,
    updateMissionPanel,
  };
}
