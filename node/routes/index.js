var express = require('express');
var router = express.Router();

/* GET home page. */
router.use(function(req, res, next) {
  return res.format({
    'html': function() {
      return res.render('index');
    },
    'json': function() {
      return res.json({
        'type': 'text',
        'value': 'Welcome to Pour'
      });
    },
    'default': function() {
      return res.status(406).send('unacceptable request format');
    }
  });
});

module.exports = router;
