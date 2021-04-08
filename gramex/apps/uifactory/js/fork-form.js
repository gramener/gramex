/* exported initiate_copy */

/**
  * Make a copy of the form
  * @param {string} base
  * @param {number} form_id
*/
function initiate_copy(base, form_id) {
  // fetch form details
  fetch(`${base}/publish?id=${form_id}`)
    .then(response => response.json())
    .then(function (response) {
      let form_details = response[0]
      delete form_details.id

      // when a form is duplicated if it's a template ensure the resultant form isn't a template
      // check for the flag and delete it
      form_details.metadata = JSON.parse(form_details.metadata)
      if(Object.keys(form_details.metadata).includes('template'))
        delete form_details.metadata.template
      form_details.metadata = JSON.stringify(form_details.metadata)

      // remove id attribute, publish and redirect to /create?id=NEW_ID or /form/NEW_ID
      $.ajax(`${base}/publish`, {
        method: 'POST',
        data: form_details,
        success: function (response) {
          $('.toast-body').html('Copy successful. Redirecting to new form.')
          $('.toast').toast('show')
          setTimeout(function () {
            window.location.href = `${base}/create?id=${response.data.inserted[0].id}`
          }, 2000)
        }
      })
    })
}
