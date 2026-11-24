// Dalil Legal — Modern JS 3D Interactive Effects (3D Tilt & Metallic Gold Canvas)
(function() {
  'use strict';

  // 1. Interactive 3D Card Tilt with Specular Glare
  function init3DTilt() {
    const cards = document.querySelectorAll('.luxury-card, .calc-wrapper, .demo, .feat-card');
    
    cards.forEach(card => {
      // Create glare overlay if not present
      let glare = card.querySelector('.glare-3d');
      if (!glare) {
        glare = document.createElement('div');
        glare.className = 'glare-3d';
        glare.style.position = 'absolute';
        glare.style.top = '0';
        glare.style.left = '0';
        glare.style.right = '0';
        glare.style.bottom = '0';
        glare.style.borderRadius = 'inherit';
        glare.style.pointerEvents = 'none';
        glare.style.opacity = '0';
        glare.style.transition = 'opacity 0.25s ease';
        glare.style.background = 'radial-gradient(circle at 50% 50%, rgba(255,255,255,0.7) 0%, rgba(200,164,92,0.15) 50%, transparent 75%)';
        glare.style.zIndex = '5';
        card.style.position = card.style.position === 'absolute' ? 'absolute' : 'relative';
        card.appendChild(glare);
      }

      card.style.transformStyle = 'preserve-3d';
      card.style.transition = 'transform 0.15s ease-out, box-shadow 0.25s ease';

      function handleMove(e) {
        const rect = card.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        const centerX = rect.width / 2;
        const centerY = rect.height / 2;
        
        const rotateX = ((y - centerY) / centerY) * -7; // Max tilt 7 deg
        const rotateY = ((x - centerX) / centerX) * 7;

        card.style.transform = `perspective(1000px) rotateX(${rotateX.toFixed(2)}deg) rotateY(${rotateY.toFixed(2)}deg) translateY(-4px) scale3d(1.01, 1.01, 1.01)`;
        card.style.boxShadow = '0 20px 40px rgba(200, 164, 92, 0.2)';
        
        glare.style.opacity = '1';
        glare.style.background = `radial-gradient(circle at ${(x/rect.width*100).toFixed(1)}% ${(y/rect.height*100).toFixed(1)}%, rgba(255,255,255,0.6) 0%, rgba(200,164,92,0.2) 40%, transparent 70%)`;
      }

      function handleLeave() {
        card.style.transform = 'perspective(1000px) rotateX(0deg) rotateY(0deg) translateY(0) scale3d(1, 1, 1)';
        card.style.boxShadow = '';
        glare.style.opacity = '0';
      }

      card.addEventListener('mousemove', handleMove);
      card.addEventListener('mouseleave', handleLeave);
    });
  }

  // 2. Interactive 3D Gold Legal Emblem Canvas Animation
  function init3DHeroCanvas() {
    const canvasContainer = document.getElementById('hero3DCanvasContainer');
    if (!canvasContainer) return;

    const canvas = document.createElement('canvas');
    canvas.id = 'hero3DCanvas';
    canvas.style.width = '100%';
    canvas.style.height = '100%';
    canvas.style.display = 'block';
    canvasContainer.innerHTML = '';
    canvasContainer.appendChild(canvas);

    const ctx = canvas.getContext('2d');
    let width, height;
    let mouseX = 0, mouseY = 0;
    let targetX = 0, targetY = 0;
    let angle = 0;

    function resize() {
      const rect = canvasContainer.getBoundingClientRect();
      width = canvas.width = rect.width * (window.devicePixelRatio || 1);
      height = canvas.height = rect.height * (window.devicePixelRatio || 1);
    }
    resize();
    window.addEventListener('resize', resize);

    window.addEventListener('mousemove', (e) => {
      const rect = canvas.getBoundingClientRect();
      targetX = ((e.clientX - rect.left) / rect.width - 0.5) * 2;
      targetY = ((e.clientY - rect.top) / rect.height - 0.5) * 2;
    });

    function draw() {
      ctx.clearRect(0, 0, width, height);

      // Smooth mouse damping
      mouseX += (targetX - mouseX) * 0.05;
      mouseY += (targetY - mouseY) * 0.05;
      angle += 0.012;

      const cx = width / 2;
      const cy = height / 2;
      const radius = Math.min(width, height) * 0.32;

      ctx.save();
      ctx.translate(cx, cy);

      // 3D Parallax tilt transform
      const tiltX = mouseY * 0.45;
      const tiltY = mouseX * 0.45;

      // Outer Rotating 3D Ring with Gold Gradient
      ctx.beginPath();
      for (let i = 0; i <= 360; i += 5) {
        const rad = (i * Math.PI) / 180 + angle;
        const x = Math.cos(rad) * radius * Math.cos(tiltY);
        const y = Math.sin(rad) * radius * Math.cos(tiltX) + Math.sin(rad) * Math.sin(tiltY) * 15;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.closePath();
      ctx.lineWidth = 4 * (window.devicePixelRatio || 1);
      ctx.strokeStyle = '#C8A45C';
      ctx.shadowColor = 'rgba(200, 164, 92, 0.4)';
      ctx.shadowBlur = 16;
      ctx.stroke();

      // Inner Counter-rotating 3D Ring
      ctx.beginPath();
      for (let i = 0; i <= 360; i += 6) {
        const rad = (i * Math.PI) / 180 - angle * 0.8;
        const r2 = radius * 0.82;
        const x = Math.cos(rad) * r2 * Math.cos(tiltY);
        const y = Math.sin(rad) * r2 * Math.cos(tiltX);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.closePath();
      ctx.lineWidth = 2 * (window.devicePixelRatio || 1);
      ctx.strokeStyle = '#8A6A2A';
      ctx.shadowBlur = 8;
      ctx.stroke();

      // Central Floating Scales Emblem with 3D Depth
      const scaleOffsetX = mouseX * 22;
      const scaleOffsetY = mouseY * 18;

      ctx.save();
      ctx.translate(scaleOffsetX, scaleOffsetY);

      // Central Pillar
      ctx.beginPath();
      ctx.moveTo(0, -radius * 0.45);
      ctx.lineTo(0, radius * 0.45);
      ctx.lineWidth = 6 * (window.devicePixelRatio || 1);
      ctx.strokeStyle = '#A98538';
      ctx.stroke();

      // Beam with subtle dynamic rocking
      const beamAngle = Math.sin(angle * 1.5) * 0.08 + mouseX * 0.12;
      ctx.save();
      ctx.rotate(beamAngle);

      ctx.beginPath();
      ctx.moveTo(-radius * 0.45, -radius * 0.35);
      ctx.lineTo(radius * 0.45, -radius * 0.35);
      ctx.lineWidth = 5 * (window.devicePixelRatio || 1);
      ctx.strokeStyle = '#C8A45C';
      ctx.stroke();

      // Left and right pans
      const panOffset = radius * 0.45;
      [-panOffset, panOffset].forEach(px => {
        ctx.beginPath();
        ctx.arc(px, -radius * 0.15, radius * 0.18, 0, Math.PI);
        ctx.closePath();
        ctx.fillStyle = 'rgba(200, 164, 92, 0.25)';
        ctx.fill();
        ctx.lineWidth = 2.5 * (window.devicePixelRatio || 1);
        ctx.strokeStyle = '#C8A45C';
        ctx.stroke();

        // Chains
        ctx.beginPath();
        ctx.moveTo(px - radius * 0.15, -radius * 0.15);
        ctx.lineTo(px, -radius * 0.35);
        ctx.moveTo(px + radius * 0.15, -radius * 0.15);
        ctx.lineTo(px, -radius * 0.35);
        ctx.lineWidth = 1.5 * (window.devicePixelRatio || 1);
        ctx.strokeStyle = '#8A6A2A';
        ctx.stroke();
      });

      ctx.restore();
      ctx.restore();

      ctx.restore();

      requestAnimationFrame(draw);
    }
    draw();
  }

  // Initialize after DOM load
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      init3DTilt();
      init3DHeroCanvas();
    });
  } else {
    init3DTilt();
    init3DHeroCanvas();
  }

  window.Dalil3D = {
    refresh: init3DTilt,
    initHeroCanvas: init3DHeroCanvas
  };
})();

