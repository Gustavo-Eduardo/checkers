const p = document.getElementById("python-data");
window.detection.onUpdatePointer((pointer) => {
    p.innerHTML = pointer; 
})