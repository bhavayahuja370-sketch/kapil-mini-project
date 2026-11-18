let stream, running = false;
const video = document.querySelector('#camera'), statusText = document.querySelector('#scanstatus');
function stopCamera() { running = false; if(stream) stream.getTracks().forEach(t => t.stop()); video.srcObject = null; }
function submitCode(code) { stopCamera(); document.querySelector('#token').value = code; document.querySelector('#scanform').requestSubmit(); }
function detector() { if (!('BarcodeDetector' in window)) throw new Error('QR detection is unavailable in this browser. Try Chrome / Edge, or use a USB QR scanner and the code field.'); return new BarcodeDetector({formats:['qr_code']}); }
document.querySelector('#start').onclick = async () => {
  stopCamera();
  try { const reader = detector(); stream = await navigator.mediaDevices.getUserMedia({video:{facingMode:'environment'}}); video.srcObject=stream; await video.play(); running=true; statusText.textContent='Ready. Hold a QR pass inside the camera view.';
    async function scan() { if(!running)return; try { const codes=await reader.detect(video); if(codes.length){submitCode(codes[0].rawValue);return;} } catch(e) { statusText.textContent='Keep the QR steady and well lit.'; } if(running)setTimeout(scan,300); } scan();
  } catch(e) {stopCamera(); statusText.textContent=e.message;}
};
document.querySelector('#stop').onclick=stopCamera;
document.querySelector('#qrfile').onchange=async e=>{let bitmap; try{const file=e.target.files[0];if(!file)return;const reader=detector();bitmap=await createImageBitmap(file);const codes=await reader.detect(bitmap);if(codes.length)submitCode(codes[0].rawValue);else statusText.textContent='No QR code found. Try a clearer image.';}catch(err){statusText.textContent=err.message;}finally{if(bitmap)bitmap.close();}};
document.querySelector('#search').oninput=e=>{document.querySelectorAll('tbody tr').forEach(row=>row.hidden=!row.textContent.toLowerCase().includes(e.target.value.toLowerCase()));};
window.addEventListener('pagehide',stopCamera);
