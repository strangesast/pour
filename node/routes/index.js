var express = require('express');
var router = express.Router();
var Kegerator = require('../models/kegerator');

/* GET home page. */
router.get('/', function(req, res, next) {
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

router.get('/temps', function(req, res, next) {
  Kegerator.find({}).then(function(kegs) {
    var vals = {'kegs' : kegs};
    return res.json(vals);
  });
});

module.exports = router;
