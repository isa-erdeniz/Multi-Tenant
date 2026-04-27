/* Wardrobe Form - Step Wizard */
let currentStep = 1;
const totalSteps = 4;

function showStep(step) {
  document.querySelectorAll('.form-step').forEach(function(el) {
    el.classList.remove('active');
    el.classList.add('hidden');
  });

  const target = document.getElementById('step-' + step);
  if (target) {
    target.classList.remove('hidden');
    target.classList.add('active');
  }

  document.querySelectorAll('.step-dot').forEach(function(dot, index) {
    if (index + 1 <= step) {
      dot.classList.add('active');
    } else {
      dot.classList.remove('active');
    }
  });

  currentStep = step;
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function nextStep(step) {
  if (!validateStep(currentStep)) return;
  showStep(step);
}

function prevStep(step) {
  showStep(step);
}

function validateStep(step) {
  const section = document.getElementById('step-' + step);
  if (!section) return true;

  const requiredFields = section.querySelectorAll('[required]');
  let valid = true;

  requiredFields.forEach(function(field) {
    const value = field.type === 'file' ? field.files?.length : (field.value || '').trim();
    if (!value) {
      field.style.borderColor = '#F44336';
      valid = false;
    } else {
      field.style.borderColor = '';
    }
  });

  if (!valid) {
    alert('Lütfen zorunlu alanları doldurun.');
  }
  return valid;
}

document.addEventListener('DOMContentLoaded', function() {
  var formEl = document.querySelector('form[data-initial-step]');
  var startStep = formEl ? parseInt(formEl.getAttribute('data-initial-step'), 10) : 1;
  showStep(startStep);

  document.querySelectorAll('.step-dot').forEach(function(dot) {
    dot.addEventListener('click', function() {
      var stepNum = parseInt(this.getAttribute('data-step'), 10);
      if (stepNum <= currentStep) {
        showStep(stepNum);
      } else if (stepNum === currentStep + 1 && validateStep(currentStep)) {
        showStep(stepNum);
      }
    });
  });

  var imageInput = document.querySelector('input[name="image"]');
  if (imageInput) {
    imageInput.addEventListener('change', function(e) {
      var file = e.target.files[0];
      if (file) {
        var reader = new FileReader();
        reader.onload = function(ev) {
          var uploadArea = document.querySelector('.upload-area');
          if (uploadArea) {
            var oldImg = uploadArea.querySelector('img');
            var placeholder = uploadArea.querySelector('.upload-placeholder');
            if (oldImg) oldImg.remove();
            if (placeholder) placeholder.style.display = 'none';
            var img = document.createElement('img');
            img.src = ev.target.result;
            img.alt = 'Önizleme';
            img.className = 'max-h-[250px] object-contain rounded-lg';
            uploadArea.appendChild(img);
          }
          if (currentStep === 1 && validateStep(1)) {
            nextStep(2);
          }
        };
        reader.readAsDataURL(file);
      }
    });
  }

  var formEl = document.querySelector('form[enctype="multipart/form-data"]');
  if (formEl) {
    formEl.addEventListener('submit', function() {
      var overlay = document.getElementById('form-loading-overlay');
      if (overlay) overlay.classList.remove('hidden');
    });
  }

  var colorHexInput = document.querySelector('input[name="color_hex"][type="color"]');
  var colorNameInput = document.querySelector('input[name="color"]');
  if (colorHexInput && colorNameInput) {
    colorHexInput.addEventListener('input', function() {
      colorNameInput.value = this.value;
    });
    colorHexInput.addEventListener('change', function() {
      colorNameInput.value = this.value;
    });
  }

});
