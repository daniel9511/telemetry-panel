/**
 * ==========================================================================
 * J.A.R.V.I.S. STANDALONE VISUALIZER & SIMULATOR COMPONENT
 * ==========================================================================
 */

// 1. PROCEDURAL AUDIO SIMULATION ENGINE (With Calibrated Settings)
class StandaloneAudioSim {
  constructor() {
    this.simSpeed = 0.6;     // Calibrated Simulation Speed
    this.simBpm = 128;       // Calibrated BPM rhythm
    this.simComplexity = 4;  // Calibrated Complexity
    this.gainValue = 1.0;    // Gain multiplier
    
    this.bufferLength = 256;
    this.freqData = new Uint8Array(this.bufferLength);
    this.timeData = new Uint8Array(this.bufferLength);
    
    this.simPhase = 0;
    this.lastSimTime = performance.now();
    this.simBeatTriggered = false;
    this.simBeatTimer = 0;
  }

  update() {
    const now = performance.now();
    const dt = (now - this.lastSimTime) / 1000;
    this.lastSimTime = now;
    
    // Accumulate simulation phase
    this.simPhase += dt * this.simSpeed * 2.0;
    
    // BPM rhythm simulation
    const beatInterval = 60 / this.simBpm; 
    this.simBeatTimer += dt * this.simSpeed;
    
    if (this.simBeatTimer >= beatInterval) {
      this.simBeatTimer %= beatInterval;
      this.simBeatTriggered = true;
    } else {
      this.simBeatTriggered = false;
    }
    
    const bpmFreqRad = (this.simBpm / 60) * Math.PI * 2;
    const timeSec = now / 1000;
    const beatDecay = Math.max(0, 1 - (this.simBeatTimer / (beatInterval * 0.4)));
    
    for (let i = 0; i < this.bufferLength; i++) {
      const t = i / this.bufferLength;
      let amplitude = 0;
      
      // 1. Bass Peak
      if (t < 0.15) {
        amplitude = (0.4 + 0.6 * beatDecay) * 180;
        amplitude += Math.sin(timeSec * 5) * 20; 
        amplitude += Math.random() * 15; 
      }
      // 2. Mid frequencies
      else if (t < 0.6) {
        let wave = 0;
        for (let c = 1; c <= this.simComplexity; c++) {
          wave += Math.sin(this.simPhase * (c * 1.8) + t * (c * 12)) * (1 / c);
        }
        const midBeatMod = 0.7 + 0.3 * Math.sin(this.simPhase * 0.8);
        amplitude = (0.2 + 0.3 * Math.abs(wave) + 0.1 * beatDecay) * 160 * midBeatMod;
        amplitude += Math.random() * 10;
      }
      // 3. High frequencies
      else {
        const hatSpeed = bpmFreqRad * 2;
        const hatTrigger = Math.abs(Math.sin(timeSec * hatSpeed));
        const hatVolume = hatTrigger > 0.85 ? (hatTrigger - 0.85) / 0.15 : 0.05;
        
        amplitude = (0.05 + 0.25 * hatVolume) * 140;
        amplitude += Math.random() * 25 * (1 - t * 0.4); 
      }
      
      amplitude *= this.gainValue;
      this.freqData[i] = Math.max(0, Math.min(255, amplitude));
      
      const timeWave = Math.sin(this.simPhase * 8 + t * 40) * (this.freqData[i] * 0.4);
      this.timeData[i] = Math.max(0, Math.min(255, 128 + timeWave));
    }
  }

  getAverages() {
    let bassSum = 0;
    let midSum = 0;
    let trebleSum = 0;
    let totalSum = 0;
    
    const len = this.bufferLength;
    const bassLimit = Math.floor(len * 0.15);
    const midLimit = Math.floor(len * 0.60);
    
    for (let i = 0; i < len; i++) {
      const val = this.freqData[i];
      totalSum += val * val;
      
      if (i < bassLimit) bassSum += val;
      else if (i < midLimit) midSum += val;
      else trebleSum += val;
    }
    
    const rms = Math.sqrt(totalSum / len) / 255;
    
    return {
      bass: (bassSum / bassLimit) / 255,
      mid: (midSum / (midLimit - bassLimit)) / 255,
      treble: (trebleSum / (len - midLimit)) / 255,
      rms: Math.min(1.0, rms * 1.5)
    };
  }

  isTransientDetected() {
    return this.simBeatTriggered;
  }
}

// 2. CANVAS PROCEDURAL RENDERER ENGINE
class JarvisVisualizer {
  constructor(canvasId, audioEngine) {
    this.canvas = document.getElementById(canvasId);
    this.ctx = this.canvas.getContext('2d');
    this.audioEngine = audioEngine;
    
    // Hardcoded Visual Parameters (matching settings)
    this.coreScale = 1.0;
    this.ringCount = 5;
    this.particleCount = 80;
    this.glowIntensity = 15;
    this.trailDecay = 0.15;
    this.coreStyle = 'arc-reactor';
    
    this.coreAngle = 0;
    this.ringAngles = Array(12).fill(0).map(() => Math.random() * Math.PI * 2);
    this.particles = [];
    
    // Cyan palette color theme
    this.themeColors = {
      solid: 'rgb(0, 240, 255)',
      glow: 'rgba(0, 240, 255, 0.6)',
      dim: 'rgba(0, 240, 255, 0.25)',
      faint: 'rgba(0, 240, 255, 0.08)'
    };
    
    this.lastTime = performance.now();
    this.glitchTimer = 0;
    
    window.addEventListener('resize', () => this.resizeCanvases());
    this.resizeCanvases();
  }

  resizeCanvases() {
    const parent = this.canvas.parentElement;
    const dpr = window.devicePixelRatio || 1;
    this.canvas.width = parent.clientWidth * dpr;
    this.canvas.height = parent.clientHeight * dpr;
    this.ctx.scale(dpr, dpr);
  }

  resolveThemeColors() {
    // Attempt to pull dynamically from CSS variables, fall back to default Cyan
    const style = window.getComputedStyle(document.body);
    this.themeColors.solid = style.getPropertyValue('--glow-color-solid').trim() || 'rgb(0, 240, 255)';
    this.themeColors.glow = style.getPropertyValue('--glow-color').trim() || 'rgba(0, 240, 255, 0.6)';
    this.themeColors.dim = style.getPropertyValue('--glow-color-dim').trim() || 'rgba(0, 240, 255, 0.25)';
    this.themeColors.faint = style.getPropertyValue('--glow-color-faint').trim() || 'rgba(0, 240, 255, 0.08)';
  }

  updateParticles(averages, transientDetected, dt) {
    while (this.particles.length < this.particleCount) {
      this.particles.push(this.createParticle(true));
    }
    if (this.particles.length > this.particleCount) {
      this.particles.length = this.particleCount;
    }
    
    if (transientDetected) {
      const burstCount = Math.floor(this.particleCount * 0.2);
      for (let i = 0; i < burstCount; i++) {
        const idx = Math.floor(Math.random() * this.particles.length);
        if (this.particles[idx]) {
          this.particles[idx] = this.createParticle(false, true);
        }
      }
    }
    
    const speedMultiplier = 0.15 + averages.treble * 0.45; // Calibrated particle speed
    
    for (let p of this.particles) {
      if (p.isBurst) {
        p.radius += p.radialSpeed * speedMultiplier * dt * 60;
        p.life -= dt;
        p.alpha = Math.max(0, p.life / p.maxLife);
        
        if (p.life <= 0 || p.radius > 400) {
          Object.assign(p, this.createParticle(true));
        }
      } else {
        p.angle += p.orbitSpeed * speedMultiplier * dt;
        const drift = Math.sin(performance.now() * 0.002 + p.speedPhase) * 12 * averages.bass;
        p.radius = p.baseRadius + drift;
        if (p.alpha < 1) p.alpha += dt * 2;
      }
    }
  }

  createParticle(randomPos = true, isBurst = false) {
    const minRadius = 60 * this.coreScale;
    const maxRadius = 240;
    const baseRadius = randomPos ? (minRadius + Math.random() * (maxRadius - minRadius)) : minRadius;
    const angle = Math.random() * Math.PI * 2;
    
    if (isBurst) {
      const maxLife = 0.8 + Math.random() * 0.6;
      return {
        isBurst: true,
        angle: angle,
        radius: minRadius,
        radialSpeed: 2.5 + Math.random() * 4.0,
        size: 1 + Math.random() * 2,
        alpha: 1.0,
        life: maxLife,
        maxLife: maxLife
      };
    } else {
      return {
        isBurst: false,
        angle: angle,
        baseRadius: baseRadius,
        radius: baseRadius,
        orbitSpeed: (0.15 + Math.random() * 0.3) * (Math.random() > 0.5 ? 1 : -1),
        speedPhase: Math.random() * 100,
        size: 0.8 + Math.random() * 1.8,
        alpha: 0.1,
        life: 1.0,
        maxLife: 1.0
      };
    }
  }

  draw(timestamp) {
    this.resolveThemeColors();
    
    const dt = Math.max(0, Math.min(0.03, (timestamp - this.lastTime) / 1000));
    this.lastTime = timestamp;
    
    // Auto-resize trigger
    const parent = this.canvas.parentElement;
    const dpr = window.devicePixelRatio || 1;
    const expectedWidth = parent.clientWidth * dpr;
    const expectedHeight = parent.clientHeight * dpr;
    
    if (this.canvas.width !== expectedWidth || this.canvas.height !== expectedHeight) {
      this.resizeCanvases();
    }
    
    const width = this.canvas.width / dpr;
    const height = this.canvas.height / dpr;
    const centerX = width / 2;
    const centerY = height / 2;
    
    const averages = this.audioEngine.getAverages();
    const isBeat = this.audioEngine.isTransientDetected();
    
    this.coreAngle += (0.04 + averages.bass * 0.26) * dt * 60 * (Math.PI / 180); // Calibrated core spin
    this.updateParticles(averages, isBeat, dt);
    
    // Motion trail blur
    this.ctx.fillStyle = `rgba(3, 5, 13, ${this.trailDecay})`;
    this.ctx.fillRect(0, 0, width, height);
    
    // Glitch effect trigger
    if (isBeat && Math.random() > 0.7 && this.glitchTimer <= 0) {
      this.glitchTimer = 0.08;
    }
    
    this.ctx.save();
    if (this.glitchTimer > 0) {
      this.glitchTimer -= dt;
      if (Math.random() > 0.4) {
        const sliceY = Math.random() * height;
        const sliceH = 20 + Math.random() * 60;
        const offset = -15 + Math.random() * 30;
        this.ctx.drawImage(this.canvas, 0, sliceY, width, sliceH, offset, sliceY, width, sliceH);
        
        this.ctx.strokeStyle = this.themeColors.solid;
        this.ctx.lineWidth = 0.5;
        this.ctx.beginPath();
        this.ctx.moveTo(0, sliceY);
        this.ctx.lineTo(width, sliceY);
        this.ctx.stroke();
      }
    }
    
    // Draw components
    this.drawRadarGrid(this.ctx, centerX, centerY, width, height);
    this.drawParticles(this.ctx, centerX, centerY);
    this.drawConcentricRings(this.ctx, centerX, centerY, averages, dt);
    this.drawReactorCore(this.ctx, centerX, centerY, averages);
    
    this.ctx.restore();
  }

  drawRadarGrid(ctx, cx, cy, w, h) {
    ctx.save();
    ctx.strokeStyle = this.themeColors.faint;
    ctx.lineWidth = 1;
    
    const maxRadius = Math.max(w, h) * 0.45;
    for (let r = 80; r < maxRadius; r += 80) {
      ctx.beginPath();
      ctx.arc(cx, cy, r, 0, Math.PI * 2);
      ctx.stroke();
    }
    
    ctx.beginPath();
    ctx.moveTo(cx - 300, cy); ctx.lineTo(cx - 100, cy);
    ctx.moveTo(cx + 100, cy); ctx.lineTo(cx + 300, cy);
    ctx.moveTo(cx, cy - 300); ctx.lineTo(cx, cy - 100);
    ctx.moveTo(cx, cy + 100); ctx.lineTo(cx, cy + 300);
    ctx.stroke();
    ctx.restore();
  }

  drawParticles(ctx, cx, cy) {
    ctx.save();
    ctx.shadowBlur = this.glowIntensity * 0.6;
    ctx.shadowColor = this.themeColors.solid;
    
    for (let p of this.particles) {
      ctx.fillStyle = this.themeColors.solid;
      ctx.globalAlpha = p.alpha;
      
      const px = cx + Math.cos(p.angle) * p.radius;
      const py = cy + Math.sin(p.angle) * p.radius;
      
      ctx.beginPath();
      ctx.arc(px, py, p.size, 0, Math.PI * 2);
      ctx.fill();
      
      if (!p.isBurst && p.alpha > 0.3) {
        ctx.strokeStyle = this.themeColors.solid;
        ctx.lineWidth = p.size * 0.4;
        ctx.globalAlpha = p.alpha * 0.25;
        
        ctx.beginPath();
        const trailLen = p.orbitSpeed * 0.3;
        ctx.arc(cx, cy, p.radius, p.angle, p.angle - trailLen, p.orbitSpeed > 0);
        ctx.stroke();
      }
    }
    ctx.restore();
  }

  drawConcentricRings(ctx, cx, cy, averages, dt) {
    ctx.save();
    
    const baseRadius = 65 * this.coreScale;
    const ringSpacing = 28;
    const audioData = this.audioEngine.freqData;
    const dataLen = audioData.length;
    
    for (let r = 0; r < this.ringCount; r++) {
      const radius = baseRadius + (r + 1) * ringSpacing;
      const direction = (r % 2 === 0) ? 1 : -1;
      
      let freqValue = 0;
      if (r === 0) freqValue = averages.bass;
      else if (r === 1) freqValue = (averages.bass + averages.mid) / 2;
      else if (r === 2) freqValue = averages.mid;
      else if (r === 3) freqValue = (averages.mid + averages.treble) / 2;
      else freqValue = averages.treble;
      
      const angleSpeed = (0.012 + freqValue * 0.13) * direction; // Calibrated ring spin
      this.ringAngles[r] += angleSpeed * dt * 60;
      
      ctx.strokeStyle = this.themeColors.solid;
      ctx.shadowColor = this.themeColors.solid;
      ctx.shadowBlur = this.glowIntensity * 0.5 * freqValue;
      
      if (r === 0) {
        ctx.lineWidth = 2;
        ctx.globalAlpha = 0.15 + freqValue * 0.65;
        const segments = 4;
        const segmentAngle = (Math.PI * 2) / segments;
        const gap = 0.35 + (1 - freqValue) * 0.4;
        
        for (let s = 0; s < segments; s++) {
          const start = this.ringAngles[r] + s * segmentAngle;
          const end = start + segmentAngle - gap;
          ctx.beginPath();
          ctx.arc(cx, cy, radius, start, end);
          ctx.stroke();
        }
      } 
      else if (r === 1) {
        ctx.lineWidth = 1;
        ctx.globalAlpha = 0.2 + freqValue * 0.5;
        const tickCount = 48;
        const tickLength = 5 + freqValue * 10;
        
        for (let i = 0; i < tickCount; i++) {
          const angle = this.ringAngles[r] + (i * Math.PI * 2) / tickCount;
          const x1 = cx + Math.cos(angle) * (radius - 2);
          const y1 = cy + Math.sin(angle) * (radius - 2);
          const x2 = cx + Math.cos(angle) * (radius + tickLength - 2);
          const y2 = cy + Math.sin(angle) * (radius + tickLength - 2);
          
          ctx.beginPath();
          ctx.moveTo(x1, y1);
          ctx.lineTo(x2, y2);
          ctx.stroke();
        }
      }
      else if (r === 2) {
        ctx.lineWidth = 1.5;
        ctx.globalAlpha = 0.5 + freqValue * 0.4;
        const barCount = 64;
        const startBin = Math.floor(dataLen * 0.15);
        const step = Math.floor((dataLen * 0.65) / barCount);
        
        for (let i = 0; i < barCount; i++) {
          const angle = this.ringAngles[r] + (i * Math.PI * 2) / barCount;
          const audioIdx = startBin + (i * step);
          const ampVal = (audioData[audioIdx] / 255) * 25 * this.coreScale;
          
          const x1 = cx + Math.cos(angle) * radius;
          const y1 = cy + Math.sin(angle) * radius;
          const x2 = cx + Math.cos(angle) * (radius + ampVal);
          const y2 = cy + Math.sin(angle) * (radius + ampVal);
          
          ctx.beginPath();
          ctx.moveTo(x1, y1);
          ctx.lineTo(x2, y2);
          ctx.stroke();
        }
      }
      else if (r === 3) {
        ctx.lineWidth = 0.8;
        ctx.globalAlpha = 0.35;
        
        // draw full circles (spinning text labels removed per feedback)
        ctx.beginPath();
        ctx.arc(cx, cy, radius, 0, Math.PI * 2);
        ctx.stroke();
        ctx.beginPath();
        ctx.arc(cx, cy, radius + 4, 0, Math.PI * 2);
        ctx.stroke();
      }
      else {
        ctx.lineWidth = 1;
        ctx.globalAlpha = 0.1 + freqValue * 0.6;
        const segments = 3;
        const arcLength = Math.PI * 0.25;
        
        for (let s = 0; s < segments; s++) {
          const start = this.ringAngles[r] + (s * Math.PI * 2) / segments;
          const end = start + arcLength;
          ctx.beginPath();
          ctx.arc(cx, cy, radius, start, end);
          ctx.stroke();
          
          const ex = cx + Math.cos(end) * radius;
          const ey = cy + Math.sin(end) * radius;
          ctx.beginPath();
          ctx.arc(ex, ey, 2, 0, Math.PI * 2);
          ctx.fill();
        }
      }
    }
    ctx.restore();
  }

  drawReactorCore(ctx, cx, cy, averages) {
    ctx.save();
    
    const corePulse = 1.0 + averages.bass * 0.28;
    const baseRadius = 45 * this.coreScale * corePulse;
    
    ctx.shadowBlur = this.glowIntensity * (0.8 + averages.bass * 0.6);
    ctx.shadowColor = this.themeColors.solid;
    
    if (this.coreStyle === 'arc-reactor') {
      ctx.strokeStyle = this.themeColors.solid;
      ctx.lineWidth = 3;
      ctx.globalAlpha = 0.8;
      ctx.beginPath();
      ctx.arc(cx, cy, baseRadius, 0, Math.PI * 2);
      ctx.stroke();
      
      ctx.lineWidth = 2;
      const cellCount = 8;
      const angleStep = (Math.PI * 2) / cellCount;
      const cellGap = 0.16;
      
      ctx.save();
      ctx.translate(cx, cy);
      ctx.rotate(this.coreAngle);
      for (let i = 0; i < cellCount; i++) {
        const start = i * angleStep + cellGap;
        const end = (i + 1) * angleStep - cellGap;
        
        ctx.beginPath();
        ctx.arc(0, 0, baseRadius - 6, start, end);
        ctx.lineTo(Math.cos(end) * (baseRadius - 16), Math.sin(end) * (baseRadius - 16));
        ctx.arc(0, 0, baseRadius - 16, end, start, true);
        ctx.closePath();
        ctx.stroke();
      }
      ctx.restore();
      
      ctx.fillStyle = this.themeColors.solid;
      ctx.globalAlpha = 0.9;
      ctx.beginPath();
      ctx.arc(cx, cy, baseRadius * 0.35, 0, Math.PI * 2);
      ctx.fill();
      
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 1;
      ctx.shadowBlur = 10;
      ctx.shadowColor = '#ffffff';
      ctx.beginPath();
      for (let i = 0; i < 4; i++) {
        const spikeAngle = Math.random() * Math.PI * 2;
        const len = (baseRadius * 0.1) + Math.random() * (baseRadius * 0.25);
        ctx.moveTo(cx, cy);
        ctx.lineTo(cx + Math.cos(spikeAngle) * len, cy + Math.sin(spikeAngle) * len);
      }
      ctx.stroke();
    }
    ctx.restore();
  }
}

// 3. INITIALIZE STANDALONE RUNNER
document.addEventListener('DOMContentLoaded', () => {
  const audioSim = new StandaloneAudioSim();
  const visualizer = new JarvisVisualizer('jarvis-canvas', audioSim);
  
  function render(timestamp) {
    audioSim.update();
    visualizer.draw(timestamp);
    requestAnimationFrame(render);
  }
  
  requestAnimationFrame(render);
});
