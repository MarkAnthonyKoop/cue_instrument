# CueAxe: Pool Cue as Guitar-Like Instrument

## Concept

A playable pool cue with embedded sensors producing both analog and digital audio signals. The natural wood vibration stays in the analog domain (direct to wire/amp like an electric guitar), while digital sensors handle finger position, pressure mapping, and gesture modulation. A companion app processes the digital channels for pitch control and effects.

```
            BUTT END                              TIP
  [Battery|MCU|Laser] =============================> [Ferrule]
   30mm dia                                          13mm dia
   
   |<-- Electronics -->|<----- Active Play Zone ----->|
   |     (~200mm)      |        (~600mm)              |
```

---

## Signal Architecture

### Analog Path (vibration -> sound)

The cue's natural acoustic vibration is captured and sent directly to a 1/4" jack or wireless transmitter with **zero digital conversion**. This preserves the organic, woody character of the instrument.

**Primary pickup: Piezo cable** running the length of the shaft in a shallow routed channel. Piezo cable (TE Raychem type) generates voltage along its entire length from mechanical vibration. Frequency response 20Hz-20kHz. This is effectively a distributed contact microphone that captures the cue's tap tones, strike resonances, and any bowing/scraping.

**Secondary pickup: PVDF film strips** at 2-3 positions along the shaft. These thin (28-110um) polymer film sensors have broader frequency response than PZT ceramics and are flexible enough to conform to the curvature. Positioned at vibrational antinodes for maximum sensitivity.

**Optional: Embedded steel wire** running in a channel along the top of the cue. Tensioned between two bridge points. Paired with a miniature electromagnetic pickup (6mm bobbin, neodymium magnet, ~5000 turns of 42AWG wire). The wire can be plucked, bowed, or struck like a monochord string. Tension is preset but could be adjustable via a tuning peg in the butt cap. This gives a true magnetic pickup tone alongside the piezo signal.

**Analog signal chain:**
```
Piezo cable/PVDF --> JFET buffer (high-Z input) --> Volume pot --> 
  --> 1/4" jack (direct to amp)
  --> Bluetooth audio transmitter (optional, adds latency)

EM pickup (if present) --> Separate output or summed with piezo
```

The JFET buffer is critical - piezo elements have extremely high output impedance (megohms). Without buffering at the source, cable capacitance kills high frequencies. A single 2N5457 JFET in source-follower configuration, powered by the onboard battery, handles this.

### Digital Path (sensors -> app -> pitch/effects)

All position, pressure, gesture, and control data flows through a microcontroller to the companion app via BLE (Bluetooth Low Energy). The app maps sensor data to musical parameters and generates/modifies the synthesized pitch.

```
Capacitive touch array --|
Pressure (Velostat)    --|--> MCU (ESP32-S3) --> BLE --> Phone App
Accelerometer/Gyro     --|                                  |
Buttons/controls       --|                                  v
                                                    Audio output
                                                    (synth/effects)
```

---

## Sensor Stack

### 1. Finger Position Along the Cue (Axial)

**Technology: Cypress CapSense (PSoC 4100S)**

Copper electrode strips routed longitudinally along a ~600mm active zone on the shaft. 16 electrodes at ~37mm spacing with centroid interpolation achieves **sub-millimeter resolution** for continuous finger position.

The electrodes are thin copper traces on a flex PCB that wraps around part of the cue's circumference, covered by a 0.2-0.5mm lacquer/clearcoat dielectric. The player's finger changes capacitance as it slides along the shaft - exactly like a giant capacitive slider.

**Mapping:** The app maps the continuous position value to pitch. This is where the guitar analogy comes in - sliding your hand toward the tip raises pitch (shorter vibrating length), sliding toward the butt lowers it. The app can quantize to chromatic/diatonic scales or allow continuous (fretless) pitch.

### 2. Finger Position Around the Cue (Radial)

**Technology: FDC2214 (TI) capacitance-to-digital converter**

8 radial electrode strips arranged at 45-degree intervals around the circumference, each running the full length of the active zone. The FDC2214's 28-bit resolution with sub-femtofarad sensitivity can determine which radial sector(s) the finger contacts.

**Mapping options:**
- **Vibrato/pitch bend:** Rotating finger pressure around the cue modulates pitch up/down
- **Timbre control:** Angular position crossfades between different oscillator waveforms or filter settings
- **Modulation wheel:** Continuous CC output for any synth parameter
- **Chord voicing:** Different angular positions select chord intervals above the root

This is unique to the cylindrical form factor - no guitar can do this.

### 3. Pressure / Dynamics

**Technology: Velostat piezoresistive strip**

A Velostat layer sandwiched between the radial capacitive electrodes and an outer conductive fabric layer. Scanned as a resistive matrix using the same electrode grid. Pressure sensitivity adds dynamics - light touch for pianissimo, firm grip for fortissimo.

**Resolution:** ~5mm spatial, ~256 pressure levels after ADC (10-bit with nonlinear correction).

**Gotchas:** Velostat has significant hysteresis and drift. Fine for expressive musical control (relative dynamics), not for absolute force measurement. Logarithmic response actually matches musical dynamics perception well.

### 4. Spatial Motion & Gesture

**Technology: MPU-6050 (6-axis accel + gyro) + sensor fusion**

Mounted in the butt end. The IMU gives full 3D orientation and motion, opening up an entire dimension of expression that no flat instrument can match. Sensor fusion (complementary filter or Madgwick/Mahony algorithm on the ESP32) converts raw accel/gyro into stable orientation quaternions at 100Hz+.

#### Axis Mapping

```
                    Y (vertical)
                    ^
                    |    Cue held horizontally = neutral
                    |   /
                    |  /
                    | /
   Z (roll axis) --+---------> X (horizontal sweep)
   (along cue)     |
                   
   Tilt UP    = pitch raise (whammy bar UP)
   Tilt DOWN  = pitch drop (whammy bar DOWN / dive bomb)
   Sweep LEFT/RIGHT = pan, phaser, or assignable
   Roll (spin around cue axis) = special gestures
```

#### Vertical Motion -> Whammy

Lifting the tip of the cue raises pitch; dropping it dives. This maps the Y-axis tilt angle (from horizontal neutral) to a pitch bend range (configurable: +/- 2 semitones to +/- octave). 

The feel is natural - it's the same body mechanic as a whammy bar on a guitar, but using your whole arm. Deadzone around horizontal prevents accidental bends during normal play.

**Implementation:** `pitch_bend = clamp((tilt_angle - deadzone) * sensitivity, -8192, 8191)` sent as MIDI pitch bend at 100Hz.

#### Horizontal Sweep -> Expression

Sweeping the cue left/right (yaw change, detected via gyro Z integration or magnetometer if added) maps to a second expression axis. Default mappings:
- **Phaser / flanger sweep** - wave the cue side to side for a jet-plane swoosh
- **Stereo pan** - the sound follows the cue's direction in the stereo field
- **Wah-wah** - horizontal sweep controls a bandpass filter, like rocking a wah pedal
- **Assignable CC** - any MIDI control change

#### Spin -> Special Effects

**Three-finger spin** (rolling the cue between thumb, index, and middle finger so it rotates around its own long axis):

The gyroscope Z-axis (aligned with the cue) detects spin rate. This is a unique gestural input impossible on any other instrument.

**Spin mappings:**
- **Leslie/rotary speaker simulation** - spin rate directly controls the virtual speaker rotation speed. Slow spin = gentle chorus. Fast spin = full-tilt Leslie scream. This is *viscerally* satisfying because the physical rotation matches the sonic rotation.
- **Tremolo rate** - spin speed modulates amplitude tremolo rate
- **Glitch/stutter** - above a spin threshold, trigger rhythmic buffer-repeat effects. The faster you spin, the faster the glitch rate.
- **Tape stop / tape start** - flick-spin in one direction = tape speed-up effect. Reverse spin = tape slow-down. 
- **Ring modulator** - spin rate modulates the ring mod carrier frequency
- **Harmonic sweep** - spin position (angular phase from gyro integration) selects which harmonic of the current note is emphasized

**Spin detection details:** The MPU-6050 gyro Z-axis measures angular velocity up to +/-2000 deg/sec. A casual three-finger roll is ~200-500 deg/sec. A fast spin can hit 1000+. The firmware applies a high-pass filter to isolate intentional spin from gradual drift, and a threshold to distinguish spin from normal handling rotation.

#### Strike / Percussion

Sharp acceleration spikes (>5g on any axis) are detected as strikes:
- **Tip strike** (poking motion) - triggers a percussive hit / note onset
- **Side slap** - triggers a different percussion sample (snare, clap)
- **Butt thump** (tapping the butt on a surface) - kick drum trigger
- Acceleration magnitude maps to velocity (MIDI 0-127)

#### Compound Gestures

The app can detect gesture combinations:
- **Tilt + spin** = pitch bend with vibrato (whammy + Leslie simultaneously)
- **Sweep + pressure increase** = wah-wah with volume swell
- **Quick flip** (180-degree rotation) = octave jump or kill switch stutter
- **Pendulum swing** = auto-wah at the swing frequency

### 5. Aiming Laser

**Technology: 5mW 650nm (red) or 520nm (green) laser module**

Mounted in the butt cap, aimed along the cue axis. Dual purpose:
1. **Pool aiming** - projects a dot on the table for shot alignment
2. **Beam-break position reference** - the laser beam travels along the cue's surface; a phone camera can potentially detect where a finger interrupts or scatters the beam

Class 3R safety compliance required. Momentary switch activation (button on butt cap).

---

## Microcontroller

**ESP32-S3** - the right choice here:
- Dual-core 240MHz, enough for scanning all sensor matrices
- Native BLE 5.0 (low latency audio/MIDI over BLE)
- 20 ADC channels (12-bit) for analog sensors
- I2C/SPI for digital sensors (CapSense, FDC2214, MPU-6050)
- USB-C for charging and firmware updates
- Small module (18x25mm) fits in the butt section
- ~$4 in volume

**Firmware responsibilities:**
- Scan capacitive matrix at 200Hz+ (5ms latency budget)
- Read pressure matrix at 100Hz
- Read IMU at 1kHz, run Madgwick sensor fusion at 100Hz for stable orientation
- Detect spin (gyro Z high-pass filter + threshold), strikes (accel spike >5g), gestures
- Package all data into BLE MIDI or OSC messages (orientation as 14-bit pitch bend + CCs)
- Manage battery (LiPo charge controller)
- Laser on/off control

---

## Output: The Cue as Speaker

**Technology: Dayton Audio DAEX25FHE-4 surface exciter**

A 25mm exciter epoxied inside the hollowed butt section turns the entire wooden cue into a resonant speaker. The player feels the vibration of their notes through their hands - haptic feedback that makes the instrument feel alive.

- 40W power handling, 4 ohm
- Frequency response ~200Hz-17kHz on wood
- Driven by a small class-D amp board (PAM8403, $2)
- Weight: ~30g

**Feedback management:** Since the piezo pickup and exciter share the same wooden body, acoustic feedback (howling) is a real risk. Mitigations:
- Notch filter on the exciter input at the cue's primary resonance frequencies
- Keep exciter volume low (it's for haptic feel, not room-filling sound)
- Phase inversion feedback cancellation in the app

---

## Companion App

### Core Functions

1. **Pitch engine** - Maps axial finger position to pitch (configurable: chromatic, scale-locked, fretless glide)
2. **Sound synthesis** - Generates audio from the digital sensor data. Can blend with the analog piezo signal.
3. **Radial mapping** - Assigns angular finger position to any parameter
4. **Spatial motion engine** - Processes IMU orientation for whammy (vertical), expression (horizontal), and spin effects (Leslie, tremolo, glitch)
5. **Gesture recognition** - Detects compound gestures (flip, strike, spin+tilt) and maps to discrete events
6. **Tuning/calibration** - Learns the player's hand position range, adjusts sensitivity, sets whammy deadzone
7. **Presets** - Store and recall complete mappings (sensor assignments, scale, spin effect, etc.)

### Signal Flow in App

```
BLE MIDI/OSC input
    |
    +--> Pitch engine (axial position -> frequency)
    |       |
    |       v
    +--> Synthesizer (wavetable/FM/physical modeling)
    |       |
    |       +--> [Radial position -> timbre/filter]
    |       +--> [Pressure -> amplitude/dynamics]  
    |       +--> [Vertical tilt -> whammy/pitch bend]
    |       +--> [Horizontal sweep -> wah/phaser/pan]
    |       +--> [Spin rate -> Leslie/tremolo/glitch]
    |       +--> [Strike -> percussion trigger]
    |       |
    |       v
    +--> Mixer (blend synth + analog input from cue)
    |       |
    |       v
    +--> Output (headphones / amp / exciter-back-to-cue)
```

### Eulerian Magnification Mode (Analysis Tool)

Not for real-time performance, but a built-in analysis mode:
- Phone camera pointed at the cue while it vibrates
- Slow-mo capture at 240fps
- Post-processing amplifies subtle vibration modes
- Visualizes node/antinode positions along the shaft
- Helps the player (and builder) understand the cue's acoustics
- Useful during calibration and development

---

## Physical Construction

### Cross-Section at Butt End (~30mm dia)

```
        Outer lacquer (0.3mm)
       /
      /  Velostat pressure layer (0.1mm)
     /  /
    /  /  Copper radial electrodes (flex PCB, 0.1mm)
   /  /  /
  /  /  /   Maple shaft (structural)
 |  |  |  /
 |  |  |  |   +-----------+
 |  |  |  |   | Hollowed  |
 |  |  |  |   | cavity:   |
 |  |  |  |   | ESP32     |
 |  |  |  |   | LiPo      |
 |  |  |  |   | Amp board |
 |  |  |  |   | Exciter   |
 |  |  |  |   +-----------+
 |  |  |  |
 |  |  |  \  Piezo cable in routed channel
  \  \  \
   \  \  Axial capacitive electrodes (flex PCB)
    \  \
     Steel wire in channel (optional EM pickup)
```

### Cross-Section at Active Zone (~20mm dia)

```
     Lacquer
    / Velostat
   / / Radial electrodes (8 strips)
  / / / Maple
 | | | |
 | | | +-- Piezo cable (routed channel, top)
 | | | +-- Steel wire (routed channel, opposite side)
 | | |
  \ \ \ Axial electrodes (flex PCB, half-wrap)
```

### Weight Budget

| Component | Weight |
|---|---|
| Stock pool cue | ~540g (19oz) |
| ESP32-S3 module | 5g |
| LiPo battery (500mAh) | 12g |
| Flex PCBs + electrodes | 15g |
| Velostat layer | 5g |
| Piezo cable | 10g |
| DAEX25 exciter | 30g |
| Amp board + misc electronics | 15g |
| Steel wire + EM pickup (optional) | 20g |
| **Total** | **~650g (23oz)** |

Standard pool cues are 18-21oz. At 23oz this is heavy but playable - some break cues run 25oz+. The extra weight is concentrated in the butt (electronics cavity), which actually helps balance since you want the center of gravity toward the grip.

### Power

- **LiPo:** 3.7V 500mAh in the butt cavity. ESP32 + sensors draw ~80-150mA. Runtime ~3-4 hours.
- **Charging:** USB-C port in the butt cap (or inductive charging pad in the case)
- **Analog path:** The JFET buffer draws <1mA and could run on a coin cell independently, so the analog signal works even if the digital system is dead

---

## Bill of Materials (Prototype)

| Component | Part | Qty | Unit Cost | Total |
|---|---|---|---|---|
| MCU | ESP32-S3-WROOM-1 | 1 | $4 | $4 |
| Capacitive sensing | Cypress PSoC 4100S | 1 | $3 | $3 |
| Cap-to-digital | TI FDC2214 | 1 | $5 | $5 |
| IMU | MPU-6050 breakout | 1 | $3 | $3 |
| Piezo cable | TE coaxial, 1.5m | 1 | $15 | $15 |
| PVDF film | TE LDT0-028K | 3 | $8 | $24 |
| Velostat sheet | 30x30cm | 1 | $6 | $6 |
| Flex PCB (electrodes) | Custom, JLCPCB | 2 | $10 | $20 |
| JFET buffer | 2N5457 + passives | 1 | $2 | $2 |
| Exciter | Dayton DAEX25FHE-4 | 1 | $12 | $12 |
| Amp board | PAM8403 | 1 | $2 | $2 |
| Laser module | 5mW 520nm green | 1 | $5 | $5 |
| LiPo battery | 3.7V 500mAh | 1 | $5 | $5 |
| USB-C charge board | TP4056 | 1 | $1 | $1 |
| Pool cue (donor) | Maple, 2-piece | 1 | $30 | $30 |
| Steel wire | 0.3mm piano wire, 1m | 1 | $3 | $3 |
| EM pickup (mini) | Custom wound | 1 | $5 | $5 |
| Connectors, wire, misc | - | - | $10 | $10 |
| **Total** | | | | **~$155** |

---

## Development Phases

### Phase 1: Analog Core
- Route channel in donor cue, install piezo cable
- Build JFET buffer circuit, wire to 1/4" jack
- Verify vibration pickup: tap the cue, hear it through an amp
- Characterize frequency response with Audacity spectrum analyzer
- Use Eulerian magnification (phone slow-mo + OpenCV) to visualize vibration modes

### Phase 2: Digital Position Sensing  
- Build capacitive electrode flex PCB
- Program PSoC 4100S for linear slider with centroid interpolation
- Test finger position resolution on flat prototype, then wrap around cue
- Add FDC2214 for radial sensing
- Implement BLE MIDI output from ESP32

### Phase 3: App MVP
- Basic pitch engine: axial position -> MIDI note
- Simple synth (sine/saw) responding to finger position
- Radial position -> pitch bend
- IMU tilt -> filter cutoff
- Bluetooth MIDI connection to ESP32

### Phase 4: Expression & Output
- Add Velostat pressure layer
- Map pressure to velocity/dynamics
- Install exciter for haptic feedback
- Implement feedback cancellation
- Add laser module with momentary switch

### Phase 5: Integration & Refinement
- Fit all electronics into the butt cavity
- Final weight balance
- Polished app with presets
- Cable strain relief and waterproofing for sweat
- Optional: embed steel wire + EM pickup for dual analog sources

---

## Open Questions

1. **Latency budget:** BLE MIDI adds ~10-20ms. Acceptable for synth control, but the analog path must remain zero-latency for the organic feel.
2. **Playability as a pool cue:** How much can we modify the shaft before it stops being a functional cue? The balance, tip, and ferrule must remain intact.
3. **Sweat and grip chalk:** Pool players use chalk and sometimes gloves. How does this affect capacitive sensing? May need auto-calibration.
4. **Regulatory:** Laser safety classification for the aiming beam. BLE/FCC certification for production.
5. **String tension vs. structural integrity:** Can the cue handle a tensioned steel wire without warping over time?
