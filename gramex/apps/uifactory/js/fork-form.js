/* exported initiate_copy */

/**
  * Make a copy of the form
  * @param {string} base      - base path of the action
  * @param {number} form_id   - form identifier
  * @param {boolean} template - flag to make a form as template
*/
function initiate_copy(base, form_id, template) {
  fetch(`${base}/publish?id=${form_id}`)
    .then(response => response.json())
    .then(function (response) {
      let form_details = response[0]
      form_details.metadata = JSON.parse(form_details.metadata)
      delete form_details.thumbnail

      if(!template) {
        delete form_details.id
        // when a form is duplicated if it's a template ensure the resultant form isn't a template
        // check for the flag and delete it
        if(Object.keys(form_details.metadata).includes('template'))
          delete form_details.metadata.template
      } else {
        // make a form a template
        form_details.metadata.template = 1
      }
      form_details.metadata = JSON.stringify(form_details.metadata)

      // remove id attribute, publish and redirect to /create?id=NEW_ID or /form/NEW_ID
      $.ajax(`${base}/publish`, {
        method: !template ? 'POST' : 'PUT',
        data: form_details,
        success: function (response) {
          $('.toast-body').html('Copy successful. Redirecting to new form.')
          $('.toast').toast('show')
          setTimeout(function () {
            // refresh the forms when an existing form is made a template
            // else redirect to the newly created form after Copy action
            if(!template)
              window.location.href = `${base}/create?id=${response.data.inserted[0].id}`
            else
              render_forms()
          }, 2000)
        }
      })
    })
}
